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
  X(Uid, "", "user id"),						\
    X(VmPeak, "U=kB", "Peak vm size"),					\
    X(VmSize, "U=kB", "Current vm size"),				\
    X(VmLck, "U=kB", "Locked mem size"),				\
    X(VmHWM, "U=kB", "Peak resident set size"),				\
    X(VmRSS, "U=kB", "Current resident set size"),			\
    X(VmData, "U=kB", "size of data"),					\
    X(VmStk, "U=kB", "size of stack"),					\
    X(VmExe, "U=kB", "size of text"),					\
    X(VmLib, "U=kB", "shared lib code size"),				\
    X(VmPTE, "U=kB", "page table entry size"),				\
    X(VmSwap, "U=kB", "swapped vm size"),				\
    X(Threads, "", "number of threads"),				\
    X(Cpus_allowed_list, "", "cores process can use"),			\
    X(Mems_allowed_list, "", "memory nodes process can use"),		\
    
static void proc_collect_pid(struct stats_type *type, const char *pid)
{
  struct stats *stats = NULL;
  char path[32];
  char process[128];
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

	if (!strcmp("bash", rest) || !strcmp("ssh", rest) || 
	    !strcmp("sshd", rest) || !strcmp("metacity", rest))
	  goto out;
  
	snprintf(process, sizeof(process), "%s/%s", rest, pid);
	stats = get_current_stats(type, process);
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
  if (fnmatch("[1-9]*", dir->d_name, 0))
    return 0;

  struct stat dirinfo;

  int len = strlen(dir->d_name) + 7; 
  char path[len];

  strcpy(path, "/proc/");
  strcat(path, dir->d_name);

  if (stat(path, &dirinfo) < 0 || dirinfo.st_uid == 0) {
    TRACE("Do not include this proc entry %s", path);
    return 0;
  }

  struct passwd *pwd;
  pwd = getpwuid(dirinfo.st_uid);
  if (pwd == NULL || !strcmp("postfix", pwd->pw_name) || !strcmp("rpc", pwd->pw_name) || !strcmp("rpcuser", pwd->pw_name) || !strcmp("dbus", pwd->pw_name) || 
      !strcmp("daemon", pwd->pw_name) || !strcmp("ntp", pwd->pw_name))
    return 0;
  
  return 1;
}

static void proc_collect(struct stats_type *type) 
{

  struct dirent **namelist;
  int n;

  n = scandir("/proc", &namelist, filter, 0);
  if (n < 0)
    ERROR("Not enough memory.");
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
