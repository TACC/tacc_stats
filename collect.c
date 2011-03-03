#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include "stats.h"
#include "trace.h"
#include "collect.h"

int collect_single(unsigned long long *dest, const char *path)
{
  int rc = -1;
  FILE *file = NULL;
  unsigned long long val;

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  if (fscanf(file, "%llu", &val) == 1) {
    *dest = val;
    rc = 0;
  }

 out:
  if (file != NULL)
    fclose(file);

  return rc;
}

int collect_key_value_file(struct stats *stats, const char *path)
{
  int rc = 0;
  FILE *file = NULL;
  char *line = NULL;
  size_t line_size = 0;

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    rc = -1;
    goto out;
  }

  while (getline(&line, &line_size, file) >= 0) {
    char *key, *rest = line;
    unsigned long long val;

    key = strsep(&rest, " \t\n");
    if (key[0] == 0)
      continue;
    if (rest == NULL)
      continue;

    errno = 0;
    val = strtoull(rest, NULL, 0);
    if (errno == 0)
      stats_set(stats, key, val);
  }

 out:
  free(line);
  if (file != NULL)
    fclose(file);

  return rc;
}

int collect_key_value_dir(struct stats *stats, const char *dir_path)
{
  int rc = 0;
  DIR *dir = NULL;
  char *path = NULL;

  dir = opendir(dir_path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", dir_path);
    rc = -1;
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    free(path);
    path = NULL;

    if (ent->d_name[0] == '.')
      continue;

    if (asprintf(&path, "%s/%s", dir_path, ent->d_name) < 0) {
      ERROR("cannot allocate path: %m\n");
      continue;
    }

    unsigned long long val = 0;
    if (collect_single(&val, path) < 0)
      continue;

    stats_set(stats, ent->d_name, val);
  }

 out:
  free(path);
  if (dir != NULL)
    closedir(dir);

  return rc;
}
