/*! \file cpu_is_snb.h

  \brief Check CPUID vendor and signature.  
 */

//! Get CPU signature
static void get_cpuid_signature(int cpuid_file, char* signature)
{
  int ebx = 0, ecx = 0, edx = 0, eax = 1;
  __asm__ ("cpuid": "=b" (ebx), "=c" (ecx), "=d" (edx), "=a" (eax):"a" (eax));

  int model = (eax & 0x0FF) >> 4;
  int extended_model = (eax & 0xF0000) >> 12;
  int family_code = (eax & 0xF00) >> 8;
  int extended_family_code = (eax & 0xFF00000) >> 16;

  snprintf(signature,sizeof(signature),"%02x_%x", extended_family_code | family_code, extended_model | model);

}

//! Test if signature is Haswell
static int cpu_is_haswell(char *cpu)
{
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[4];
  int rc = 0;
  char signature[5];

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
    goto out; /* CentaurHauls? */

  get_cpuid_signature(cpuid_fd,signature);
  TRACE("cpu%s, CPUID Signature %s\n", cpu, signature);
  if (strncmp(signature, "06_3c", 5) !=0 && strncmp(signature, "06_45", 5) !=0 && strncmp(signature, "06_46", 5) !=0 && strncmp(signature, "06_47", 5) !=0 && strncmp(signature, "06_3f", 5) !=0)
    goto out;

  rc = 1;

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

