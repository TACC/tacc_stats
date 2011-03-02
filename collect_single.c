#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stats.h"
#include "trace.h"

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
