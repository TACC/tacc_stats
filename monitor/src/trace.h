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

#ifdef RABBITMQ
#define logger syslog
#define logtag LOG_ERR
#else
#define logger fprintf
#define logtag stderr
#endif

#ifdef DEBUG
#define ERROR(fmt,arg...)					\
  logger(logtag, "%s:%d: "fmt, __func__, __LINE__, ##arg) 
#else
#define ERROR(fmt,arg...)						\
  logger(logtag, "%s: "fmt, program_invocation_short_name, ##arg)
#endif

#define FATAL(fmt,arg...) do { \
    ERROR(fmt, ##arg);         \
    exit(1);                   \
  } while (0)

#endif
