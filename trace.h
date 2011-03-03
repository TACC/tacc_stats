#ifndef _TRACE_H_
#define _TRACE_H_
#include <stdio.h>
#include <errno.h>

#ifdef DEBUG
#define TRACE ERROR
#else
#define TRACE(fmt,arg...) ((void) 0)
#endif

#define ERROR(fmt,arg...) \
  fprintf(stderr, "%s: "fmt, program_invocation_short_name, ##arg)

#define FATAL(fmt,arg...) do { \
    ERROR(fmt, ##arg);         \
    exit(1);                   \
  } while (0)

#endif
