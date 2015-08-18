#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <getopt.h>
#include <signal.h>
#include <malloc.h>
#include <errno.h>
#include <sys/time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/syslog.h>
#include "cpuid_discover.h"

int main() {

  int i, nr_cpus;

  nr_cpus = sysconf(_SC_NPROCESSORS_ONLN);  
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);
    cpu_snb(cpu);
  }

  return 0;
}

