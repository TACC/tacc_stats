#ifndef _STATS_H_
#define _STATS_H_
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include "dict.h"
#include "trace.h"
#include "schema.h"
#include "STRJOIN.h"

#define TACC_STATS_PROGRAM "tacc_stats"
#define TACC_STATS_VERSION "1.0.0"

struct stats_type {
  char *st_name;
  int (*st_begin)(struct stats_type *type);
  void (*st_collect)(struct stats_type *type);
  char *st_schema_def;
  struct schema st_schema;
  struct dict st_current_dict;
  unsigned int st_enabled:1, st_selected:1;
};

struct stats {
  struct stats_type *s_type;
  unsigned long long *s_val;
  char s_dev[];
};

static inline struct stats *key_to_stats(const char *key)
{
  size_t s_dev_offset = ((struct stats *) NULL)->s_dev - (char *) NULL;
  return (struct stats *) (key - s_dev_offset);
}

extern struct dict global_dict;
extern time_t current_time;
extern int nr_cpus;

struct stats_type *name_to_type(const char *name);
struct stats_type *stats_type_for_each(size_t *i);

void stats_type_wr_stats(struct stats_type *type, FILE *file);

struct stats *get_current_stats(struct stats_type *type, const char *dev);
void stats_set(struct stats *s, const char *key, unsigned long long val);
void stats_inc(struct stats *s, const char *key, unsigned long long val);

#endif
