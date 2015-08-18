/* Currently only used for intel chips after Nehalem - x2APIC chips */
/* nhm, wtm, snb, ivb, hsw are classified correctly */
/* Will autoset AMD to 4 counters */
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include "trace.h"
#include "cpuid.h"

// Return 1 for true and -1 for false
int signature(processor_t p, char *cpu, int *nr_ctrs) {

  char cpuid_path[80];
  int cpuid_fd = -1;
  unsigned buf[8];
  char vendor[12];
  char signature[5];
  int rc = 0;

  /* Open /dev/cpuid/CPU/cpuid. */
  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%s/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);
  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }

  /* Do cpuid 0 to get cpu vendor. */
  if (pread(cpuid_fd, buf, sizeof(buf), 0x0) < 0) {
    ERROR("cannot read cpu vendor through `%s': %m\n", cpuid_path);
    goto out;
  }
  buf[0] = buf[2], buf[2] = buf[3], buf[3] = buf[0];
  snprintf(vendor, sizeof(vendor) + 1, (char*) buf + 4);
  TRACE("cpu %s, vendor `%.12s'\n", cpu, vendor);

  /* Do cpuid 1 to get cpu family. */
  if (pread(cpuid_fd, buf, sizeof(buf), 0x01) < 0) {
    ERROR("cannot read cpu signature through `%s': %m\n", cpuid_path);
    goto out;
  }
  // int stepping = regs[0] & 0xF;
  unsigned model  = ((buf[0] & 0x00F0000) >> 12) | ((buf[0] & 0x0FF) >> 4);
  unsigned family = ((buf[0] & 0xFF00000) >> 16) | ((buf[0] & 0xF00) >> 8);
  snprintf(signature, sizeof(signature) + 1,"%02x_%x", family, model);
  TRACE("cpu %s, signature %.5s\n", cpu, signature);

  if (strncmp(vendor, "GenuineIntel", 12) == 0) {
    if (pread(cpuid_fd, buf, sizeof(buf), 0x0A) < 0) {
      ERROR("cannot read number of performance counters through `%s': %m\n", cpuid_path);
      goto out;
    }
    *nr_ctrs = (buf[0] >> 8) & 0xFF;    
    TRACE("Number of performance counters = %d\n", *nr_ctrs);
  }
  else if (strncmp((char*) buf + 4, "AuthenticAMD", 12) == 0) {
    *nr_ctrs = 4;
  }
  else
    ERROR("cannot read number of counters through `%s': %m\n", cpuid_path);

  switch(p) {
  case NEHALEM:
    if (strncmp(vendor, "GenuineIntel", 12) == 0 && 
	(strncmp(signature, "06_1a", 5) == 0 || 
	 strncmp(signature, "06_1e", 5) == 0 || 
	 strncmp(signature, "06_1f", 5) == 0 || 
	 strncmp(signature, "06_2e", 5) == 0)) {
      rc = 1;
      TRACE("Nehalem %s\n", signature);
    }
    goto out;
  case WESTMERE:
    if (strncmp(vendor, "GenuineIntel", 12) == 0 && 
	(strncmp(signature, "06_25", 5) == 0 || 
	 strncmp(signature, "06_2c", 5) == 0 || 
	 strncmp(signature, "06_1f", 5) == 0)) {
      rc = 1;
      TRACE("Westmere %s\n", signature);
    }
    goto out;
  case IVYBRIDGE:
    if (strncmp(vendor, "GenuineIntel", 12) == 0 &&
	(strncmp(signature, "06_3a", 5) == 0 ||
	 strncmp(signature, "06_3e", 5) == 0)) {
      rc = 1;
      TRACE("Ivy Bridge %s\n", signature);
    }
    goto out;
  case SANDYBRIDGE:
    if (strncmp(vendor, "GenuineIntel", 12) == 0 && 
	(strncmp(signature, "06_2a", 5) == 0 || 
	 strncmp(signature, "06_2d", 5) == 0)) {	
      rc = 1;
      TRACE("Sandy Bridge %s\n", signature);
    }
    goto out;
  case HASWELL:
    if (strncmp(vendor, "GenuineIntel", 12) == 0 &&
	(strncmp(signature, "06_3c", 5) == 0 || 
	 strncmp(signature, "06_45", 5) == 0 || 
	 strncmp(signature, "06_46", 5) == 0 || 
	 strncmp(signature, "06_3f", 5) == 0)) {
      rc = 1;
      TRACE("Haswell %s\n", signature);
    }
    goto out;
  case BROADWELL:
    if (strncmp(vendor, "GenuineIntel", 12) == 0 &&
	(strncmp(signature, "06_3d", 5) == 0 || 
	 strncmp(signature, "06_47", 5) == 0)) {
      rc = 1;
      TRACE("Broadwell %s\n", signature);
    }
    goto out;
  case SKYLAKE:
    if (strncmp(vendor, "GenuineIntel", 12) == 0 &&
	(strncmp(signature, "06_4e", 5) == 0 || 
	 strncmp(signature, "06_5e", 5) == 0)) {
      rc = 1;
      TRACE("Skylake %s\n", signature);
    }
    goto out;
  case AMD_10H:
    if (strncmp(vendor, "AuthenticAMD", 12) != 0) {
      rc = 1;
      goto out;
    }
  default:
    ERROR("unknown processor signature %s\n",signature);
    goto out;    
  }
  
 out:
  return rc;
}
