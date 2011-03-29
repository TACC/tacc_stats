#include <string.h>
#include <malloc.h>
#include <ctype.h>
#include "split.h"
#include "strwc.h"

char **split(const char *str)
{
  char **list = NULL;
  const char *s, *t;
  size_t wc, i;

  wc = strwc(str);

  list = calloc(wc + 1, sizeof(char*));
  if (list == NULL)
    goto err;

  s = str;
  for (i = 0; i < wc; i++) {
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
  for (i = 0; i < wc; i++)
    free(list[i]);
  free(list);
  return NULL;
}

char **splitchr(const char *str, int c)
{
  char **list = NULL;
  const char *s, *t;
  size_t len = 0, i;

  s = str;
  while (*s != 0) {
    while (*s == c)
      s++;
    if (*s != 0)
      len++;
    while (*s != 0 && *s != c)
      s++;
  }

  list = calloc(len + 1, sizeof(char*));
  if (list == NULL)
    goto err;

  s = str;
  for (i = 0; i < len; i++) {
    while (*s == c)
      s++;
    t = s;
    while (*s != 0 && *s != c)
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
