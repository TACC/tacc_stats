#ifndef _BUSMAP_H_
#define _BUSMAP_H_

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "trace.h"

int get_pci_busids(char ***buses)
{
  
  FILE *devptr;
  char buf[1024];
  char **tmp;
  uint32_t bus, dev, vendor, id;
  int ctr = 0;

  if ( (devptr = fopen("/proc/bus/pci/devices","r")) == NULL ) {
    ERROR("Failed to open PCI devices file.  Cannot perform busid mapping.");
  }
  else {
    // Discover number of buses
    while (fgets(buf,sizeof(buf)-1, devptr) ) {
      if (sscanf(buf, "%2x%2x %4x%4x", &bus, &dev, &vendor, &id) == 4 && vendor == 0x8086 && id == 0x3c43) {
	ctr++;
      }
    }
    fseek(devptr, 0, SEEK_SET);
    tmp = (char **)malloc(ctr*sizeof(char *));
    ctr = 0;
    // Get bus ids
    while (fgets(buf,sizeof(buf)-1, devptr) ) {
      if (sscanf(buf, "%2x%2x %4x%4x", &bus, &dev, &vendor, &id) == 4 && vendor == 0x8086 && id == 0x3c43) {
	tmp[ctr] = (char*) malloc(4*sizeof(char));
	sprintf(tmp[ctr++], "%2x", bus);
      }
    }
    *buses = tmp;
  }
  if (devptr != NULL)
    fclose(devptr);

  return ctr;
}

#endif
