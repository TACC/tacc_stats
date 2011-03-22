#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <ctype.h>
#include "readstr.h"

char *readstr(const char *path)
{
  char *str = NULL, *s, *t;
  FILE* file = NULL;
  char *line = NULL;
  size_t size = 0;

  file = fopen(path, "r");
  if (file == NULL)
    goto out;

  if (getline(&line, &size, file) <= 0)
    goto out;

  s = line;
  while (isspace(*s))
    s++;
  t = s;
  while (*t != 0 && !isspace(*t))
    t++;

  str = malloc(t - s + 1);
  if (str == NULL)
    goto out;

  memcpy(str, s, t - s);
  str[t - s] = 0;

 out:
  free(line);
  if (file != NULL)
    fclose(file);

  return str;
}
