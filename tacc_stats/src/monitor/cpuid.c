/* Currently only used for intel chips after Nehalem - x2APIC chips */
/* nhm, wtm, snb, ivb, hsw are classified correctly */
/* Will autoset AMD to 4 counters */
#include <stdio.h>
#include <unistd.h>
#include <stdint.h>
#include <fcntl.h>
#include <string.h>
#include "trace.h"
#include "cpuid.h"

// Return 1 for true and -1 for false
int signature(processor_t p, char *cpu, int *nr_ctrs) {

  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[4];
  int rc = 0;
  char signature[5];

  char vendor[12];
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
  // int stepping = buf[0] & 0xF;
  unsigned model  = ((buf[0] & 0x00F0000) >> 12) | ((buf[0] & 0x0FF) >> 4);
  unsigned family = ((buf[0] & 0xFF00000) >> 16) | ((buf[0] & 0xF00) >> 8);
  snprintf(signature, sizeof(signature) + 1,"%02x_%x", family, model);
  TRACE("cpu %s, signature %.5s\n", cpu, signature);
  
  /* Get number of perf counters */
  if (strncmp(vendor, "GenuineIntel", 12) == 0) {
    if (pread(cpuid_fd, buf, sizeof(buf), 0x0A) < 0) {
      ERROR("cannot read number of performance counters through `%s': %m\n", cpuid_path);
      goto out;
    }
    *nr_ctrs = (buf[0] >> 8) & 0xFF;    
  }
  else if (strncmp(vendor, "AuthenticAMD", 12) == 0) {
    *nr_ctrs = 4;
  }
  else {
    ERROR("cannot read number of counters through `%s': %m\n", cpuid_path);
    goto out;
  }

  TRACE("Number of performance counters = %d\n", *nr_ctrs);

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
    if (strncmp(vendor, "AuthenticAMD", 12) == 0) {
      rc = 1;
      TRACE("AMD_10h %s\n", signature);
    }
    goto out;
  default:
    ERROR("unknown processor signature %s\n",signature);
    goto out;    
  }
  
 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

int topology(char *cpu, int *pkg_id, int *core_id, int *smt_id, int *nr_core)
{
  int i;
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[4];
  int rc = 0;

  /* Open /dev/cpuid/CPU/cpuid. */
  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%s/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);

  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }

  /* Do cpuid 0 to get max leaf. */
  if (pread(cpuid_fd, buf, sizeof(buf), 0x0) < 0) {
    ERROR("cannot read cpu vendor through `%s': %m\n", cpuid_path);
    goto out;
  }

  // Get cpuid_level
  int max_leaf = buf[0];
  if (max_leaf < 0xB) 
    goto out;

  /* Do cpuid 0xB to get cpu APIC_ID. */
  if (pread(cpuid_fd, buf, sizeof(buf), 0xB) < 0) {
    ERROR("cannot read x2APIC ID through `%s': %m\n", cpuid_path);
    goto out;
  }
  unsigned int x2APIC_ID = buf[3] & 0xFFFFFFFF;
  TRACE("APIC ID %d\n", x2APIC_ID);

  // Test for x2APIC
  int SMT_Mask_Width = -1, SMT_Select_Mask = -1;      
  int CorePlus_Mask_Width, CoreOnly_Select_Mask;
  int Pkg_Select_Mask;
  int nr_smt;
  if (buf[1] != 0)
    {
      for (i=0; i <= max_leaf; i++)
	{
	  /* Upper 32 bits gets level and lower 32 gets leaf */
	  if (pread(cpuid_fd, buf, sizeof(buf), i*0x100000000 | 0xB ) < 0) {
	    ERROR("could not read cpuid level %d through `%s': %m\n", i, cpuid_path);
	    goto out;
	  }
          TRACE("%s %d %d %X %d\n",cpuid_path,buf[0],buf[1],buf[2],buf[3]);

	  /* Number of logical processors at this level, break if 0 */
	  if ((buf[1] & 0xFFFF) == 0) 
	    break;

	  /* SMT level type from EC[16:8] = 1 */
	  if (((buf[2] >> 8) & 0xFF) == 1)
	    {	      
	      nr_smt = buf[1];
	      SMT_Mask_Width = buf[0] & 0xF;
	      SMT_Select_Mask = ~((-1) << SMT_Mask_Width);
	      *smt_id = x2APIC_ID & SMT_Select_Mask;
	    }
	  /* Core level type from EC[16:8] = 2 */
	  else if (((buf[2] >> 8) & 0xFF) == 2)
	    {	     
	      *nr_core = buf[1]/nr_smt;
	      CorePlus_Mask_Width = buf[0] & 0xF;
	      CoreOnly_Select_Mask = ~((-1) << CorePlus_Mask_Width) ^ SMT_Select_Mask;
	      *core_id = (x2APIC_ID & CoreOnly_Select_Mask) >> SMT_Mask_Width;	      
	      Pkg_Select_Mask = (-1) << CorePlus_Mask_Width;
	      *pkg_id = (x2APIC_ID & Pkg_Select_Mask) >> CorePlus_Mask_Width;
	      rc = 1;
	      break;
	    }
	}
    }
  TRACE("Number of threads/physical cores %d/%d\n", nr_smt, *nr_core);
  TRACE("Pkg_ID Core_ID SMT_ID %d %d %d\n", *pkg_id, *core_id, *smt_id);
 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}
