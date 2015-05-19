#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <dirent.h>
#include <fnmatch.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/param.h>
#include <unistd.h>
#include <pwd.h>
#include "stats.h"
#include "trace.h"
#include "string1.h"

#define KEYS                                                            \
  X(Uid, "C", "user id"),						\
    X(VmPeak, "E,U=kB", "Peak vm size"),				\
    X(VmSize, "E,U=kB", "Current vm size"),				\
    X(VmLck, "E,U=kB", "Locked mem size"),				\
    X(VmHWM, "E,U=kB", "Peak resident set size"),			\
    X(VmRSS, "E,U=kB", "Current resident set size"),			\
    X(VmData, "E,U=kB", "size of data"),				\
    X(VmStk, "E,U=kB", "size of stack"),				\
    X(VmExe, "E,U=kB", "size of text"),					\
    X(VmLib, "E,U=kB", "shared lib code size"),				\
    X(VmPTE, "E,U=kB", "page table entry size"),			\
    X(VmSwap, "E,U=kB", "swapped vm size"),				\
    X(Threads, "C", "number of threads"),				\
    X(Cpus_allowed_list, "C", "cores process can use"),			\
    X(Mems_allowed_list, "C", "memory nodes process can use"),		\
    
static void proc_collect_pid(struct stats_type *type, const char *pid)
{
  struct stats *stats = NULL;
  char path[32];
  FILE *file = NULL;
  char file_buf[4096];
  char *line = NULL;
  size_t line_size = 0;
  
  TRACE("pid %s\n", pid);

  snprintf(path, sizeof(path), "/proc/%s/status", pid);
  file = fopen(path, "r");
  
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n",path);
    goto out;
  }
  setvbuf(file, file_buf, _IOFBF, sizeof(file_buf));
  
  while (getline(&line, &line_size, file) >= 0) {
    char *key, *rest = line;
    key = wsep(&rest);
    
    if (key == NULL || rest == NULL)
	continue;
    if (strcmp(key,"Name:") == 0) 
      {
	rest[strlen(rest) - 1] = '\0';
	stats = get_current_stats(type, rest);
	continue;
      }
    if (stats == NULL)
      goto out;

    errno = 0;
    key[strlen(key) - 1] = '\0';
    
    int base = 0;
    char mask[nr_cpus];
    if (strcmp(key,"Cpus_allowed_list") == 0 || strcmp(key,"Mems_allowed_list") == 0)
      {
	memset(mask, '0', nr_cpus);
        mask[nr_cpus]='\0';
	char *range;
	char *first;
	int i, second;
	while (rest) 
	  {
	    range = strsep(&rest, ",");
	    first = strsep(&range, "-");
	    if (range) second = atoi(range);
	    else second = atoi(first);

	    for (i = atoi(first); i < MIN(second + 1, nr_cpus); i++)
	      mask[nr_cpus-i-1] = '1';
	  }
	rest = mask;
	base = 2;
      }
  
    unsigned long long val = strtoull(rest, NULL, base);
    if (errno == 0)
      stats_set(stats, key, val);
  }
  
 out:
  free(line);
  if (file != NULL)
    fclose(file);

}

int filter(const struct dirent *dir)
{
  struct passwd *pwd;
  struct stat dirinfo;

  int len = strlen(dir->d_name) + 7; 
  char path[len];

  strcpy(path, "/proc/");
  strcat(path, dir->d_name);

  if (stat(path, &dirinfo) < 0) {
    perror("processdir() ==> stat()");
    exit(EXIT_FAILURE);
  }
  pwd = getpwuid(dirinfo.st_uid);
  return !fnmatch("[1-9]*", dir->d_name, 0) && ( 0 != dirinfo.st_uid && 68 != dirinfo.st_uid && strcmp("postfix", pwd->pw_name) && strcmp("rpc", pwd->pw_name) && strcmp("rpcuser", pwd->pw_name) && strcmp("dbus", pwd->pw_name) && strcmp("daemon", pwd->pw_name) && strcmp("ntp", pwd->pw_name)); 
}

static void proc_collect(struct stats_type *type) 
{

  struct dirent **namelist;
  int n;

  n = scandir("/proc", &namelist, filter, 0);
  if (n < 0)
    perror("Not enough memory.");
  else {
    while(n--) {
      proc_collect_pid(type, namelist[n]->d_name);
      free(namelist[n]);
    }
    free(namelist);
  }
}

struct stats_type proc_stats_type = {
  .st_name = "proc",
  .st_collect = &proc_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X

};
