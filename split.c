#define _GNU_SOURCE
#include <string.h>
#include <malloc.h>
#include <ctype.h>
#include "split.h"

char **split(const char *str)
{
  char **list = NULL;
  const char *s, *t;
  size_t len = 0, i;

  s = str;
  while (*s != 0) {
    while (isspace(*s))
      s++;
    if (*s != 0)
      len++;
    while (*s != 0 && !isspace(*s))
      s++;
  }

  list = calloc(len + 1, sizeof(char*));
  if (list == NULL)
    goto err;

  s = str;
  for (i = 0; i < len; i++) {
    while (isspace(*s))
      s++;
    t = s;
    while (*s != 0 && !isspace(*s))
      s++;
    list[i] = malloc(s - t + 1);
    if (list[i] == NULL)
      goto err;
    memcpy(list[i], t, s - t);
    list[i][s - t] = 0;
  }

  return list;

 err:
  for (i = 0; i < len; i++)
    free(list[i]);
  free(list);
  return NULL;
}
