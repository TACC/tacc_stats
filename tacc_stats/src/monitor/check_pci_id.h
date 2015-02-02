/*! \file check_pci_id.h
  \brief Check PCI device vendors and ids.

  If device ID is incorrect it will be skipped.
*/

static int check_pci_id(char * bus_dev, int id) {

  char pci_path[80];
  int pci_fd = -1;
  uint16_t pci_vendor;
  uint16_t pci_device;
  int rc = 0;

  snprintf(pci_path, sizeof(pci_path), "/proc/bus/pci/%s", bus_dev);
  pci_fd = open(pci_path, O_RDONLY);
  if (pread(pci_fd, &pci_vendor, sizeof(pci_vendor), 0x00) < 0 
      || pread(pci_fd, &pci_device, sizeof(pci_device), 0x02) < 0) {
    ERROR("cannot read device vendor or id: %m\n");
    goto out;
  }
  if (pci_vendor != 0x8086 || pci_device != id) goto out;

  rc = 1;
 out:
  if (pci_fd >= 0)
    close(pci_fd);
  
  return rc;
}
