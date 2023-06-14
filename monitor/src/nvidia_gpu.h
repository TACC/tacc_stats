#include <stdio.h>
#include <errno.h>
#include <limits.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <inttypes.h>

#define NFIELDS 12

// A list of avaialble dcgm metrics 
// https://github.com/NVIDIA/gpu-monitoring-tools/tree/master/etc/dcgm-exporter

#define KEYS \
  X(gpu_util,     "",     "GPU utilization in %"), \
  X(mem_util,     "",     "Memory utilization in %"), \
  X(power_usage,  "U=W",  "Power draw in Watts"), \
  X(temperature,  "U=C",  "GPU temperature in C"), \
  X(sm_active,    "",     "The ratio of cycles an SM has at least 1 warp assigned (in %)"), \
  X(sm_occupancy, "",     "The ratio of number of warps resident on an SM (in %)"), \
  X(fp64_active,  "",     "Ratio of cycles the fp64 pipes are active (in %)"), \
  X(fp32_active,  "",     "Ratio of cycles the fp32 pipes are active (in %)"), \
  X(fp16_active,  "",     "Ratio of cycles the fp16 pipes are active (in %)"), \
  X(fb_total,     "U=MB", "Framebuffer memory total (in MiB)"), \
  X(fb_used,      "U=MB", "Framebuffer memory used (in MiB)"), \
  X(fb_free,      "U=MB", "Framebuffer memory free (in MiB)")

typedef struct DCMG_DATA {
    int64_t mem_util;
    int64_t gpu_util;
    int64_t fb_total;
    int64_t fb_used;
    int64_t fb_free;
    int64_t temperature;
    double power_usage;
    double fp64_active;
    double fp32_active;
    double fp16_active;
    double sm_active;
    double sm_occupancy;
} DCMG_DATA;

