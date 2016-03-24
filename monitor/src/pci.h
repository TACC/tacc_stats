#ifndef _PCI_MAP_H
#define _PCI_MAP_H

int pci_map_create(char ***dev_paths, int *nr, int *ids, int nr_ids);
void pci_map_destroy(char ***dev_paths, int nr);

#endif
