#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>
#include <sched.h>

void cpuID(unsigned i, unsigned j, unsigned regs[4]) {

  asm volatile
    ("cpuid" : "=a" (regs[0]), "=b" (regs[1]), "=c" (regs[2]), "=d" (regs[3])
     : "a" (i), "c" (j));
}


int topology()
{
  unsigned int regs[4];
  int i;
  // Get vendor
  char vendor[12];
  cpuID(0, 0, regs);
  ((unsigned *)vendor)[0] = regs[1]; // EBX
  ((unsigned *)vendor)[1] = regs[3]; // EDX
  ((unsigned *)vendor)[2] = regs[2]; // ECX

  printf("%s\n",vendor);
  // Get cpuid_level
  int max_leaf = regs[0];

  // Get Family_Model Signature
  cpuID(1,0,regs);
  int stepping = regs[0] & 0xF;
  int model  = ((regs[0] >> 16) & 0xF) << 4 | ((regs[0] >> 4) & 0xF);
  int family = ((regs[0] >> 20) & 0xFF) << 4 | ((regs[0] >> 8) & 0xF);
  printf("%02x_%x %x\n",family,model,stepping);


  cpuID(0x0A,0,regs);
  int nr_ctrs = (regs[0] >> 8) & 0xFF;
  int ctr_width = (regs[0] >> 16) & 0xFF;

  int nr_fixed_ctrs = regs[3] & 0x1F;
  int fixed_ctr_width = (regs[3] >> 5) & 0xFF;
  
  printf("nr_ctrs %d, ctr_width %d, nr_fixed_ctrs %d, fixed_ctr_width %d\n",
	 nr_ctrs, ctr_width, nr_fixed_ctrs, fixed_ctr_width);

  cpuID(0xB,0,regs);
  unsigned int x2APIC_ID = regs[3] & 0xFFFFFFFF;

  // Test for x2APIC
  cpuID(0xB, 0, regs);
  if (regs[1] != 0)
    {
      int SMT_Mask_Width;
      int SMT_Select_Mask;      
      int CorePlus_Mask_Width;
      int CoreOnly_Select_Mask;
      int Pkg_Select_Mask;
      int SMT_ID, Core_ID, Pkg_ID;
      for (i=0;i<=max_leaf;i++)
	{
	  cpuID(0xB,i,regs);
	  if ((regs[1] & 0xFFFF) == 0) 
	    break;

	  if (i == 0)
	    {	      
	      SMT_Mask_Width = regs[0] & 0xF;
	      SMT_Select_Mask = ~((-1) << SMT_Mask_Width);
	      SMT_ID = x2APIC_ID & SMT_Select_Mask;
	    }
	  if (i == 1)
	    {	     
	      CorePlus_Mask_Width = regs[0] & 0xF;
	      CoreOnly_Select_Mask = ~((-1) << CorePlus_Mask_Width) ^ SMT_Select_Mask;
	      Core_ID = (x2APIC_ID & CoreOnly_Select_Mask) >> SMT_Mask_Width;	      
	      Pkg_Select_Mask = (-1) << CorePlus_Mask_Width;
	      Pkg_ID = (x2APIC_ID & Pkg_Select_Mask) >> CorePlus_Mask_Width;
	      printf("Pkg_ID Core_ID SMT_ID %d %d %d\n",Pkg_ID,Core_ID,SMT_ID);
	      break;
	    }
	}
    }

  return 0;
}

int main(int argc, char *argv[]) {

  int core;
  cpu_set_t set;
  int rc = -1;

  // Logical core count per CPU
  unsigned logical = sysconf(_SC_NPROCESSORS_ONLN);
  printf("Logical cpus: %d\n ", logical);

  for (core = 0; core < logical; core++)
    {
      CPU_ZERO( &set );
      CPU_SET( core, &set );
      printf("Logical Core %d\n",core) ;

      if (sched_setaffinity( getpid(), sizeof( cpu_set_t ), &set ))
	{
	  perror( "sched_setaffinity" );
	  goto out;
	}
      
      topology();
      printf("\n");
    }

  rc = 0;
 out:
  return rc;
}
