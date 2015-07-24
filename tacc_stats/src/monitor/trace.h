#ifndef _TRACE_H_
#define _TRACE_H_
#include <stdio.h>
#include <errno.h>
#include <syslog.h>

#ifdef DEBUG
#define TRACE ERROR
#else
static inline void TRACE(const char *fmt, ...) { }
#endif

#ifdef DEBUG
#define ERROR(fmt,arg...) \
  fprintf(stderr, "%s:%d: "fmt, __func__, __LINE__, ##arg)
#else
#define ERROR(fmt,arg...) \
  fprintf(stderr, "%s: "fmt, program_invocation_short_name, ##arg)
#endif

#define FATAL(fmt,arg...) do { \
    ERROR(fmt, ##arg);         \
    exit(1);                   \
  } while (0)

#endif
