#include <stdio.h>
#include <errno.h>
#include <limits.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include "miclib.h"
#include "stats.h"
#include "collect.h"
#include "trace.h"
#include "string1.h"
#include "nvml.h"

#define KEYS \
  X(memtotal, "U=B", ""), \
  X(memfree, "U=B", ""), \
    X(memused, "U=B", ""), \
    X(power, "U=mW", ""), \
    X(utilization, "","")

static int nvidia_gpu_collect_dev(struct stats *stats, int i)
{
  int rc = -1;

  nvmlDevice_t device;
  nvmlReturn_t ret;

  nvmlMemory_t memory;
  nvmlUtilization_t utilization;
  unsigned int power;

  ret = nvmlDeviceGetHandleByIndex(i, &device);
  if (NVML_SUCCESS != ret) {
    ERROR("NVML device was not read successfully: %s\n", nvmlErrorString(ret));
    goto out;
  }
  
  ret = nvmlDeviceSetPersistenceMode(device, 1);
  if (NVML_SUCCESS != ret)
    TRACE("NVML persistence mode was not enabled successfully: %s\n", nvmlErrorString(ret));
  
  
  char name[80];
  ret = nvmlDeviceGetName(device, name, 80);
  TRACE("%s\n",name);
  

  ret = nvmlDeviceGetUtilizationRates(device, &utilization); 
  if (NVML_SUCCESS != ret) {
    ERROR("NVML utilization was not read successfully: %s\n", nvmlErrorString(ret));
    goto out;
  }
  TRACE("utilization gpu: %d memory: %d\n", utilization.gpu, utilization.memory);

  ret = nvmlDeviceGetPowerUsage(device, &power);
  if (NVML_SUCCESS != ret) {
    ERROR("NVML power was not read successfully: %s\n", nvmlErrorString(ret));
    goto out;
  }
  TRACE("power %d\n", power);

  ret = nvmlDeviceGetMemoryInfo(device, &memory);
  if (NVML_SUCCESS != ret) {
    ERROR("NVML memory was not read successfully: %s\n", nvmlErrorString(ret));
    goto out;
  }
  TRACE("total %llu used %llu free %llu\n", memory.total, memory.used, memory.free);

  stats_set(stats, "utilization",  utilization.gpu);  
  stats_set(stats, "memtotal",     memory.total);
  stats_set(stats, "memfree",      memory.free);
  stats_set(stats, "memused",      memory.used);
  stats_set(stats, "power",        power);

  rc = 0;
  
 out:
  return rc;
}    

static void nvidia_gpu_collect(struct stats_type *type)
{
  int i, ndev;
  int nr = 0;;

  nvmlInit();
  if (NVML_SUCCESS != nvmlDeviceGetCount(&ndev)) {
    ERROR("device count was not read successfully: %m\n");
    goto out;
  }

  
  for (i = 0; i < ndev; i++) {    
    struct stats *stats = NULL;
    char dev[80];
    snprintf(dev, sizeof(dev), "%d", i);
    stats = get_current_stats(type, dev);
    if (stats == NULL)
      goto out;

    if (nvidia_gpu_collect_dev(stats, i) == 0)
      nr++;
  }
  
 out:
  if (nr == 0)
    type->st_enabled = 0;
  nvmlShutdown();
}

//! Definition of stats entry for this type
struct stats_type nvidia_gpu_stats_type = {
  .st_name = "nvidia_gpu",
  .st_collect = &nvidia_gpu_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
