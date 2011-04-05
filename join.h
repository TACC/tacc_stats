#ifndef _JOIN_H_
#define _JOIN_H_
#include <stddef.h>
#include <string.h>
#include <malloc.h>

char *join(char **list, size_t count, const char *delim)
{
  size_t len = 0;
  char *str = NULL, *dest;
  const char *src;
  int i;

  if (count > 0)
    len = strlen(list[0]);

  for (i = 1; i < count; i++)
    len += strlen(delim) + strlen(list[i]);

  str = malloc(len + 1);
  if (str == NULL)
    goto out;

  dest = str;

  if (count > 0) {
    src = list[0];
    while (*src != 0)
      *(dest++) = *(src++);
  }

  for (i = 1; i < count; i++) {
    src = delim;
    while (*src != 0)
      *(dest++) = *(src++);
    src = list[i];
    while (*src != 0)
      *(dest++) = *(src++);
  }

  *dest = 0;
 out:
  return str;
}

#endif
