#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include "stats.h"
#include "trace.h"

#define OSC_BASE "/proc/fs/lustre/osc"

static void read_lustre_target_stats(struct stats *fs_stats, const char *osc)
{
  char *path = NULL;
  FILE *file = NULL;
  char *line = NULL;
  size_t line_size = 0;

  if (asprintf(&path, "%s/%s/stats", OSC_BASE, osc) < 0) {
    ERROR("cannot create path: %m\n");
    goto out;
  }

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  // snapshot_time             1298995851.710784 secs.usecs
  // KEY                       COUNT  samples [UNITS] MIN MAX SUM SUMSQUARE
  // req_waittime              436580 samples [usec] 58 62261685 9625213391 26831627156812909
  // req_active                436580 samples [reqs] 1 15 439448 449516
  // read_bytes                658 samples [bytes] 4096 716800 5971968 1173801140224

  while (getline(&line, &line_size, file) >= 0) {
    char *key, *rest = line;
    unsigned long long val = 0;

    key = strsep(&rest, " \t");
    if (*key == 0 || rest == NULL)
      continue;

    if (sscanf(rest, "%*u samples %*s %*u %*u %llu", &val) == 1)
      stats_inc(fs_stats, key, val);
  }

 out:
  free(path);
  if (file != NULL)
    fclose(file);
  free(line);
}

static void read_lustre_stats(struct stats_type *type)
{
  const char *base_path = OSC_BASE;
  DIR *base_dir = NULL;

  base_dir = opendir(base_path);
  if (base_dir == NULL) {
    ERROR("cannot open `%s': %m\n", base_path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(base_dir)) != NULL) {
    if (*ent->d_name == '.' || strcmp(ent->d_name, "num_refs") == 0)
      continue;

    /* Entries in OSC_BASE (/proc/fs/lustre/osc) look like
       "scratch-OST0000-osc-00000101ec2ffc00".  We only want the
       filesystem name, so we kill the last three dashes in dir_name. */
    char fs_name[sizeof(ent->d_name)];
    strcpy(fs_name, ent->d_name);

    int dash_count = 0;
    char *dash;
    while (dash_count < 3 && (dash = strrchr(fs_name, '-')) != NULL) {
      dash_count++;
      *dash = 0;
    }

    struct stats *fs_stats = get_current_stats(type, fs_name);
    if (fs_stats == NULL) {
      ERROR("cannot get filesystem stats for `%s': %m\n", fs_name);
      continue;
    }

    read_lustre_target_stats(fs_stats, ent->d_name);
  }

 out:
  if (base_dir != NULL)
    closedir(base_dir);
}

struct stats_type ST_LUSTRE_TYPE = {
  .st_name = "ST_LUSTRE",
  .st_read = (void (*[])()) { &read_lustre_stats, NULL, },
};
