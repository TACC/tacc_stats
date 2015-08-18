#include <sched.h>

/*! \file cpuid_discover.h

  \brief Check CPUID vendor and signature.  
 */

#define ERROR(fmt,arg...) printf(fmt, ##arg)
#define TRACE(fmt,arg...) printf(fmt, ##arg)

int cpu_count(cpu_set_t* set)
{
  uint32_t i;
  int s = 0;
  const __cpu_mask *p = set->__bits;
  const __cpu_mask *end = &set->__bits[sizeof(cpu_set_t) / sizeof (__cpu_mask)];

  while (p < end)
    {
      __cpu_mask l = *p++;

      if (l == 0)
        {
	  continue;
        }

      for (i=0; i< (sizeof(__cpu_mask)*8); i++)
        {
	  if (l&(1UL<<i))
            {
	      s++;
            }
        }
    }

  return s;
}

//! Get CPU signature
static void get_cpuid_signature(char *cpu, char* signature)
{
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[4];

  /* Open /dev/cpuid/cpu/cpuid. */
  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%s/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);
  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }
  
  /* Get cpu vendor. */
  if (pread(cpuid_fd, buf, sizeof(buf), 0x0) < 0) {
    ERROR("cannot read cpu vendor through `%s': %m\n", cpuid_path);
    goto out;
  }

  buf[0] = buf[2], buf[2] = buf[3], buf[3] = buf[0];
  TRACE("cpu %s, vendor `%.12s'\n", cpu, (char*) buf + 4);

  if (strncmp((char*) buf + 4, "GenuineIntel", 12) != 0)
    goto out;

  int ebx = 0, ecx = 0, edx = 0, eax = 1;
  __asm__ ("cpuid" : 
	   "=b" (ebx), 
	   "=c" (ecx), 
	   "=d" (edx), 
	   "=a" (eax) 
	   : "a" (eax), "c" (ecx));

  int model = (eax & 0x0FF) >> 4;
  int extended_model = (eax & 0xF0000) >> 12;
  int family_code = (eax & 0xF00) >> 8;
  int extended_family_code = (eax & 0xFF00000) >> 16;

  cpu_set_t cpuSet;
  //CPU_ZERO(&cpuSet);
  sched_getaffinity(0,sizeof(cpu_set_t), &cpuSet);
  //int ht = (edx & 0x10000000) >> 28;
  printf("%d %d\n", cpu_count(&cpuSet), sysconf(_SC_NPROCESSORS_CONF));
  snprintf(signature,sizeof(signature),"%02x_%x", extended_family_code | family_code, extended_model | model);

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

}

//! Test if signature is Haswell
static int cpu_hsw(char *cpu)
{
  int rc = 1;
  char signature[5];

  get_cpuid_signature(cpu, signature);
  TRACE("cpu%s, CPUID Signature %s\n", cpu, signature);
  if (strncmp(signature, "06_3c", 5) !=0 && 
      strncmp(signature, "06_45", 5) !=0 && 
      strncmp(signature, "06_46", 5) !=0 && 
      strncmp(signature, "06_47", 5) !=0 && 
      strncmp(signature, "06_3f", 5) !=0)
    rc = 0;

  return rc;
}

//! Test if signature is Sandy/Ivy Bridge
static int cpu_snb(char *cpu)
{
  int rc = 1;
  char signature[5];

  get_cpuid_signature(cpu, signature);
  TRACE("cpu%s, CPUID Signature %s\n", cpu, signature);
  if (strncmp(signature, "06_3e", 5) !=0 && // IVB 
      strncmp(signature, "06_3a", 5) !=0 && // IVB
      strncmp(signature, "06_2a", 5) !=0 && // SNB
      strncmp(signature, "06_2d", 5) !=0)   // SNB
    rc = 0;

  return rc;
}

//! Test if signature is Nehalem
static int cpu_nhm(char *cpu)
{
  int rc = 1;
  char signature[5];

  get_cpuid_signature(cpu, signature);
  TRACE("cpu%s, CPUID Signature %s\n", cpu, signature);
  if (strncmp(signature, "06_1a", 5) !=0 && 
      strncmp(signature, "06_1e", 5) !=0 && 
      strncmp(signature, "06_1f", 5) !=0 && 
      strncmp(signature, "06_2e", 5) !=0)
    rc = 0;

  return rc;
}

//! Test if signature is Westmere
static int cpu_wtm(char *cpu)
{
  int rc = 1;
  char signature[5];

  get_cpuid_signature(cpu, signature);
  TRACE("cpu%s, CPUID Signature %s\n", cpu, signature);
  if (strncmp(signature, "06_25", 5) !=0 && 
      strncmp(signature, "06_2c", 5) !=0 && 
      strncmp(signature, "06_1f", 5) !=0)
    rc = 0;

  return rc;
}


