#ifndef _STRWC_H_
#define _STRWC_H_
#include <ctype.h>

static inline size_t strwc(const char *str)
{
  size_t wc = 0;
  const char *s;

  s = str;
  while (*s != 0) {
    while (isspace(*s))
      s++;
    if (*s != 0)
      wc++;
    while (*s != 0 && !isspace(*s))
      s++;
  }

  return wc;
}

#endif

