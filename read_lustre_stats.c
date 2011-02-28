#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include "stats.h"
#include "trace.h"

#define OSC_BASE "/proc/fs/lustre/osc"

void read_lustre_target_stats(const char *dir_name)
{
  struct stats *stats = NULL;
  char *path = NULL;
  FILE *file = NULL;
  char *line = NULL;
  size_t line_size = 0;

  if (asprintf(&path, "%s/%s/stats", OSC_BASE, dir_name) < 0) {
    ERROR("cannot create path: %m\n");
    goto out;
  }

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n");
    goto out;
  }

  stats = get_current_stats(ST_LUSTRE, fs_name);
  if (stats == NULL) {
    ERROR("cannot get lustre_stats for `%s': %m\n", fs_name);
    goto out;
  }

  while (getline(&line, &line_size, pipe) >= 0) {
    char *key, *rest = line;
    unsigned long long val;

    key = strsep(&rest, " \t");
    if (*key == 0 || rest == NULL)
      continue;
  




 out:
  free(path);
  if (file != NULL)
    fclose(file);
  free(line);
}

void read_lustre_stats(void)
{
  const char *path = OSC_BASE;
  DIR *dir = NULL;

  dir = opendir(path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    if (*ent->d_name == '.' || strcmp(ent->d_name, "num_refs") == 0)
      continue;
    



  }

 out:
  if (dir != NULL)
    closedir(dir);
}



  struct stats *lustre_stats = NULL;
  FILE *pipe = NULL;
  char *line = NULL;
  size_t line_size = 0;






  pipe = popen(ib_stats_cmd, "r");
  if (pipe == NULL) {
    ERROR("cannot execute `%s': %m\n", ib_stats_cmd);
    goto out;
  }

  ib_stats = get_current_stats(ST_IB, NULL);
  if (ib_stats == NULL) {
    ERROR("cannot get ib_stats: %m\n");
    goto out;
  }

  while (getline(&line, &line_size, pipe) >= 0) {
    char *key, *rest = line;
    unsigned long long val;

    key = strsep(&rest, ":");
    if (*key == 0 || rest == NULL)
      continue;

    while (*rest == '.')
      rest++;

    errno = 0;
    val = strtoull(rest, NULL, 0);
    if (errno != 0)
      continue;

    /* Data vaules are counted in units of 4 octets. */
    if (strcmp(key, "XmtData") == 0 || strcmp(key, "RcvData") == 0)
      val *= 4;

    stats_set(ib_stats, key, val);
  }

 out:
  free(line);
  if (pipe != NULL)
    pclose(pipe);
}
