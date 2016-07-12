#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include "pscanf.h"
#include "stats.h"
#include "trace.h"
#include "oib_utils.h"
//#include "oib_utils_pa.h"
#include "iba/stl_pa.h"
//#include "stl_print.h"
/* opa collects OPA HFI/PORT statistics by querying the OPA Performance Agent.
   These counters should all be 64-bit.
*/

#define KEYS \
  X(portXmitData, "E", ""),			\
    X(portRcvData, "E", ""),			\
    X(portXmitPkts, "E", ""),			\
    X(portRcvPkts, "E", ""),			\
    X(portMulticastXmitPkts, "E", ""),		\
    X(portMulticastRcvPkts, "E", ""),		\
    X(localLinkIntegrityErrors, "E", ""),	\
    X(fmConfigErrors, "E", ""),			\
    X(portRcvErrors, "E", ""),			\
    X(excessiveBufferOverruns, "E", ""),	\
    X(portRcvConstraintErrors, "E", ""),	\
    X(portRcvSwitchRelayErrors, "E", ""),	\
    X(portXmitDiscards, "E", ""),		\
    X(portXmitConstraintErrors, "E", ""),	\
    X(portRcvRemotePhysicalErrors, "E", ""),	\
    X(swPortCongestion, "E", ""),		\
    X(portXmitWait, "E", ""),			\
    X(portRcvFECN, "E", ""),			\
    X(portRcvBECN, "E", ""),			\
    X(portXmitTimeCong, "E", ""),		\
    X(portXmitWastedBW, "E", ""),		\
    X(portXmitWaitData, "E", ""),		\
    X(portRcvBubble, "E", ""),			\
    X(portMarkFECN, "E", ""),			\
    X(linkErrorRecovery, "E", ""),		\
    X(linkDowned, "E", ""),			\
    X(uncorrectableErrors, "E", "")

static void collect_hfi_port(struct stats *stats, char *hfi_name, uint32_t nodeLid, int portNumber)
{
  struct oib_port *mad_port = NULL;

  // These are used to obtain historical data saved by PM (we want live)
  uint64 imageNumber = 0;  
  int32 imageOffset = 0;  

  // Whether to report deltas
  uint32_t deltaFlag = 0;
  // User ctrs ?
  uint32_t userCntrsFlag = 0;

  // initialize connections to IB related entities 
  // Open the port
  int verbose = 0;

  // Open the port
  if ( oib_pa_client_init( &mad_port, (int)0, portNumber, (verbose ? stderr : NULL)) != 1 ) {
    ERROR("%s: failed to open the port: hfi %d, port %d\n", __func__, 1, portNumber);
    goto out;
  }

  // Historical data (about 10 images supposedly) are available from PA
  // We want live
  STL_PA_IMAGE_ID_DATA imageId = {0};
  imageId.imageNumber = imageNumber;
  imageId.imageOffset = imageOffset;

  TRACE("Getting Port Counters...\n");

  STL_PORT_COUNTERS_DATA *pPortCounters;  
  // Query the PA and get the counters for the port
  if ((pPortCounters = iba_pa_single_mad_port_counters_response_query(mad_port, nodeLid, (uint8_t)portNumber, 
								      deltaFlag, userCntrsFlag, &imageId)) == NULL) {
    ERROR("cannot query performance counters: %m\n");
    goto out;
  }
  TRACE( "PM controlled Port Counters (total) for NODELID 0x%04x, port number %u\n", nodeLid, portNumber);

#define X(n, r...)				\
  ({						\
    stats_set(stats, #n, pPortCounters->n);	\
    TRACE(#n"%20"PRIu64"\n");			\
  })
  KEYS;
#undef X

  if (pPortCounters)
    MemoryDeallocate(pPortCounters);
  
 out:  
  if (mad_port != NULL)
    oib_close_port(mad_port);
}

static void collect_opa(struct stats_type *type)
{
  const char *ib_dir_path = "/sys/class/infiniband";
  DIR *ib_dir = NULL;
  unsigned int lid = -1;

  ib_dir = opendir(ib_dir_path);
  if (ib_dir == NULL) {
    ERROR("cannot open `%s': %m\n", ib_dir_path);
    goto out;
  }

  struct dirent *hfi_ent;
  while ((hfi_ent = readdir(ib_dir)) != NULL) {
    char *hfi = hfi_ent->d_name;
    char ports_path[80];
    DIR *ports_dir = NULL;

    if (hfi[0] == '.')
      goto next_hfi;

    snprintf(ports_path, sizeof(ports_path), "%s/%s/ports", ib_dir_path, hfi);
    ports_dir = opendir(ports_path);
    if (ports_dir == NULL) {
      ERROR("cannot open `%s': %m\n", ports_path);
      goto next_hfi;
    }

    struct dirent *port_ent;
    while ((port_ent = readdir(ports_dir)) != NULL) {
      int port = atoi(port_ent->d_name);
      if (port <= 0)
        continue;

      /* Check that port is active. .../HFI/ports/PORT/state should read "4: ACTIVE." */
      int state = -1;
      char state_path[80];
      snprintf(state_path, sizeof(state_path), "/sys/class/infiniband/%s/ports/%d/state", hfi, port);
      if (pscanf(state_path, "%d", &state) != 1) {
        ERROR("cannot read state of IB HFI `%s' port %d: %m\n", hfi, port);
        continue;
      }

      if (state != 4) {
        ERROR("skipping inactive IB HFI `%s', port %d, state %d\n", hfi, port, state);
        continue;
      }

      /* Get the lid. */
      char lid_path[80];
      snprintf(lid_path, sizeof(lid_path), "/sys/class/infiniband/%s/ports/%i/lid", hfi, port);
      if (pscanf(lid_path, "%x", &lid) != 1) {
	ERROR("cannot read lid of IB HCA `%s' port %d: %m\n", hfi, port);
	continue;
      }

      /* Create dev name (HFI/PORT) and get stats for dev. */
      char dev[80];
      snprintf(dev, sizeof(dev), "%s/%d", hfi, port);
      TRACE("IB HFI `%s', port %d, dev `%s'\n", hfi, port, dev);

      struct stats *stats = get_current_stats(type, dev);
      if (stats == NULL)
        continue;

      collect_hfi_port(stats, hfi, lid, port);
    }

  next_hfi:
    if (ports_dir != NULL)
      closedir(ports_dir);
  }

 out:
  if (ib_dir != NULL)
    closedir(ib_dir);
}

struct stats_type opa_stats_type = {
  .st_name = "opa",
  .st_collect = &collect_opa,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
