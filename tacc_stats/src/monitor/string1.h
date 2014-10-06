#ifndef _STRING1_H_
#define _STRING1_H_
#include <stdio.h>
#include <stdarg.h>
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

static inline char *strf(const char *fmt, ...)
{
  char *str = NULL;
  va_list args;

  va_start(args, fmt);
  if (vasprintf(&str, fmt, args) < 0)
    str = NULL;
  va_end(args);
  return str;
}

#endif
