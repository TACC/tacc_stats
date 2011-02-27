#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stats.h"
#include "trace.h"

char *st_name[] = {
#define X(t) [t] = #t ,
#include "stats.x"
#undef X
};

int read_single(const char *path, unsigned long long *dest)
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

int read_key_value(const char *path, struct stats *stats)
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
