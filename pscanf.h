#ifndef _PSCANF_H_
#define _PSCANF_H_
#include <stdio.h>
#include <stdarg.h>

static inline int pscanf(const char *path, const char *fmt, ...)
{
  int rc = -1;
  FILE *file = NULL;
  va_list arg_list;
  va_start(arg_list, fmt);

  file = fopen(path, "r");
  if (file == NULL)
    goto out;

  rc = vfscanf(file, fmt, arg_list);

 out:
  if (file != NULL)
    fclose(file);
  va_end(arg_list);
  return rc;
}

#endif
