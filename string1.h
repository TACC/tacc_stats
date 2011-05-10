#ifndef _STRING1_H_
#define _STRING1_H_
#include <string.h>

static inline char *strsep_ne(char **ref, const char *delim)
{
  char *str;
  do
    str = strsep(ref, delim);
  while (str != NULL && *str == 0);
  return str;
}

static inline char *wsep(char **ref)
{
  return strsep_ne(ref, " \t\n\v\f\r");
}

#endif
