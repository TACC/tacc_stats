#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <stdarg.h>
#include "stats.h"
#include "trace.h"
#include "collect.h"

int collect_single(const char *path, unsigned long long *dest)
{
  int rc = 0;
  FILE *file = NULL;
  unsigned long long val;

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    rc = -1;
    goto out;
  }

  if (fscanf(file, "%llu", &val) == 1) {
    *dest = val;
    rc = 1;
  }

 out:
  if (file != NULL)
    fclose(file);

  return rc;
}

int collect_list(const char *path, ...)
{
  int rc = 0;
  FILE *file = NULL;
  va_list dest_list;
  va_start(dest_list, path);

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    rc = -1;
    goto out;
  }

  unsigned long long *dest;
  while ((dest = va_arg(dest_list, unsigned long long *)) != NULL) {

    if (fscanf(file, "%llu", dest) != 1) {
      ERROR("%s: no value\n", path);
      goto out;
    }
    rc++;
  }

 out:
  if (file != NULL)
    fclose(file);
  va_end(dest_list);

  return rc;
}

int collect_key_list(struct stats *stats, const char *path, ...)
{
  int rc = 0;
  FILE *file = NULL;
  va_list key_list;
  va_start(key_list, path);

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    rc = -1;
    goto out;
  }

  const char *key;
  while ((key = va_arg(key_list, const char *)) != NULL) {
    unsigned long long val;

    if (fscanf(file, "%llu", &val) != 1) {
      ERROR("%s: no value for key `%s'\n", path, key);
      goto out;
    }
    stats_set(stats, key, val);
    rc++;
  }

 out:
  if (file != NULL)
    fclose(file);
  va_end(key_list);

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

  dir = opendir(dir_path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", dir_path);
    rc = -1;
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    char *path = NULL;

    if (ent->d_name[0] == '.')
      goto next;

    if (asprintf(&path, "%s/%s", dir_path, ent->d_name) < 0) {
      ERROR("cannot allocate path: %m\n");
      goto next;
    }

    unsigned long long val = 0;
    if (collect_single(path, &val) != 1)
      goto next;

    stats_set(stats, ent->d_name, val);

  next:
    free(path);
  }

 out:
  if (dir != NULL)
    closedir(dir);

  return rc;
}
