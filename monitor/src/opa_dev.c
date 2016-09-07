#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include "pscanf.h"
#include "stats.h"
#include "oib_utils.h"
#include "iba/stl_pa.h"
#include "stl_print.h"
/* opa collects OPA HFI/PORT statistics by querying the OPA Performance Agent.
   These counters should all be 64-bit.
*/

static void collect_hfi_port(char *hfi_name, uint32_t nodeLid, int portNumber)
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
    fprintf(stderr, "%s: failed to open the port: hfi %d, port %d\n", __func__, 1, portNumber);
    goto out;
  }

  // Historical data (about 10 images supposedly) are available from PA
  // We want live
  STL_PA_IMAGE_ID_DATA imageId = {0};
  imageId.imageNumber = imageNumber;
  imageId.imageOffset = imageOffset;

  printf("Getting Port Counters...\n");

  STL_PORT_COUNTERS_DATA *pPortCounters;  
  // Query the PA and get the counters for the port
  pPortCounters = (STL_PORT_COUNTERS_DATA *)iba_pa_single_mad_port_counters_response_query(mad_port, nodeLid, (uint8_t)portNumber, 
								 deltaFlag, userCntrsFlag, &imageId);
    if (pPortCounters != NULL) {
      printf( "%*s%s controlled Port Counters (%s) for NODELID 0x%04x, port number %u%s:\n",
	      0, "", (pPortCounters->flags & STL_PA_PC_FLAG_USER_COUNTERS) ? "User" : "PM",
	      (pPortCounters->flags & STL_PA_PC_FLAG_DELTA) ? "delta" : "total",
	      nodeLid, portNumber,
	      (pPortCounters->flags &STL_PA_PC_FLAG_UNEXPECTED_CLEAR)?" (Unexpected Clear)":"");
      printf( "%*sPerformance: Transmit\n", 0, "");
      printf( "%*s    Xmit Data             %20"PRIu64" MB (%"PRIu64" Flits)\n",
	      0, "",
	      pPortCounters->portXmitData/FLITS_PER_MB,
	      pPortCounters->portXmitData);
      printf( "%*s    Xmit Pkts             %20"PRIu64"\n",
	      0, "",
	      pPortCounters->portXmitPkts);
      printf( "%*s    MC Xmit Pkts          %20"PRIu64"\n",
	      0, "",
	      pPortCounters->portMulticastXmitPkts);
      printf( "%*sPerformance: Receive\n",
	      0, "");
      printf( "%*s    Rcv Data              %20"PRIu64" MB (%"PRIu64" Flits)\n",
	      0, "",
	      pPortCounters->portRcvData/FLITS_PER_MB,
	      pPortCounters->portRcvData);
      printf( "%*s    Rcv Pkts              %20"PRIu64"\n",
	      0, "",
	      pPortCounters->portRcvPkts);
      printf( "%*s    MC Rcv Pkts           %20"PRIu64"\n",
	      0, "",
	      pPortCounters->portMulticastRcvPkts);
      printf( "%*sSignal Integrity Errors:             \n",
	      0, "");
      printf( "%*s    Link Quality Ind      %10u\n",
	      0, "",
	      pPortCounters->lq.s.linkQualityIndicator);
      printf( "%*s    Uncorrectable Err     %10u\n",
	      0, "",
	      pPortCounters->uncorrectableErrors);
      printf( "%*s    Link Downed           %10u\n",
	      0, "",
	      pPortCounters->linkDowned);
      printf( "%*s    Num Lanes Down        %10u\n",
	      0, "",
	      pPortCounters->lq.s.numLanesDown);
      printf( "%*s    Rcv Errors            %10u\n",
	      0, "",
	      pPortCounters->portRcvErrors);
      printf( "%*s    Exc. Buffer Overrun   %10u\n",
	      0, "",
	      pPortCounters->excessiveBufferOverruns);
      printf( "%*s    FM Config             %10u\n",
	      0, "",
	      pPortCounters->fmConfigErrors);
      printf( "%*s    Link Error Recovery   %10u\n",
	      0, "",
	      pPortCounters->linkErrorRecovery);
      printf( "%*s    Local Link Integrity  %10u\n",
	      0, "",
	      pPortCounters->localLinkIntegrityErrors);
      printf( "%*s    Rcv Rmt Phys Err      %10u\n",
	      0, "",
	      pPortCounters->portRcvRemotePhysicalErrors);
      printf( "%*sSecurity Errors:              \n",
	      0, "");
      printf( "%*s    Xmit Constraint       %10u\n",
	      0, "",
	      pPortCounters->portXmitConstraintErrors);
      printf( "%*s    Rcv Constraint        %10u\n",
	      0, "",
	      pPortCounters->portRcvConstraintErrors);
      printf( "%*sRouting and Other Errors:     \n",
	      0, "");
      printf( "%*s    Rcv Sw Relay Err      %10u\n",
	      0, "",
	      pPortCounters->portRcvSwitchRelayErrors);
      printf( "%*s    Xmit Discards         %10u\n",
	      0, "",
	      pPortCounters->portXmitDiscards);
      printf( "%*sCongestion:             \n",
	      0, "");
      printf( "%*s    Cong Discards         %10u\n",
	      0, "",
	      pPortCounters->swPortCongestion);
      printf( "%*s    Rcv FECN              %10u\n",
	      0, "",
	      pPortCounters->portRcvFECN);
      printf( "%*s    Rcv BECN              %10u\n",
	      0, "",
	      pPortCounters->portRcvBECN);
      printf( "%*s    Mark FECN             %10u\n",
	      0, "",
	      pPortCounters->portMarkFECN);
      printf( "%*s    Xmit Time Cong        %10u\n",
	      0, "",
	      pPortCounters->portXmitTimeCong);
      printf( "%*s    Xmit Wait             %10u\n",
	      0, "",
	      pPortCounters->portXmitWait);
      printf( "%*sBubbles:                 \n",
	      0, "");
      printf( "%*s    Xmit Wasted BW        %10u\n",
	      0, "",
	      pPortCounters->portXmitWastedBW);
      printf( "%*s    Xmit Wait Data        %10u\n",
	      0, "",
	      pPortCounters->portXmitWaitData);
      printf( "%*s    Rcv Bubble            %10u\n",
	      0, "",
	      pPortCounters->portRcvBubble);
    } 
    else {      
      fprintf(stderr, "Failed to receive iba_pa_single_mad_port_counters_response_query response: %s\n", iba_pa_mad_status_msg((uint8_t)portNumber));
      goto out;
    }

  if (pPortCounters)
    MemoryDeallocate(pPortCounters);
  
 out:  
  if (mad_port != NULL)
    oib_close_port(mad_port);
}

static void collect_opa()
{
  const char *ib_dir_path = "/sys/class/infiniband";
  DIR *ib_dir = NULL;
  unsigned int lid = -1;

  ib_dir = opendir(ib_dir_path);
  if (ib_dir == NULL) {
    printf("cannot open `%s': %m\n", ib_dir_path);
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
      printf("cannot open `%s': %m\n", ports_path);
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
        printf("cannot read state of IB HFI `%s' port %d: %m\n", hfi, port);
        continue;
      }

      if (state != 4) {
        printf("skipping inactive IB HFI `%s', port %d, state %d\n", hfi, port, state);
        continue;
      }

      /* Get the lid. */
      char lid_path[80];
      snprintf(lid_path, sizeof(lid_path), "/sys/class/infiniband/%s/ports/%i/lid", hfi, port);
      if (pscanf(lid_path, "%x", &lid) != 1) {
	printf("cannot read lid of IB HCA `%s' port %d: %m\n", hfi, port);
	goto out;
      }

      /* Create dev name (HFI/PORT) and get stats for dev. */
      char dev[80];
      snprintf(dev, sizeof(dev), "%s/%d", hfi, port);
      printf("IB HFI `%s', port %d, dev `%s'\n", hfi, port, dev);

      collect_hfi_port(hfi, lid, port);
    }

  next_hfi:
    if (ports_dir != NULL)
      closedir(ports_dir);
  }

 out:
  if (ib_dir != NULL)
    closedir(ib_dir);
}

int main() {
  collect_opa();
  return 0;
}
