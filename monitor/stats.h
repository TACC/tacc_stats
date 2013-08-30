#ifndef _STATS_H_
#define _STATS_H_
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include "dict.h"
#include "trace.h"
#include "schema.h"
#include "JOIN.h"

#define SCHEMA_DEF(k,o,d,r...) " " #k "," o

extern time_t current_time;
extern char current_jobid[10240];
extern int nr_cpus;

struct stats_type {
  int (*st_begin)(struct stats_type *type);
  void (*st_collect)(struct stats_type *type);
  char *st_schema_def;
  char *orig_st_schema_def; /* modified by charngda */
  struct schema st_schema;
  struct dict st_current_dict;
  unsigned int st_enabled:1, st_selected:1;
  char st_name[];
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

int stats_type_init(struct stats_type *type);
void stats_type_destroy(struct stats_type *type);
struct stats_type *stats_type_for_each(size_t *i);
struct stats_type *stats_type_get(const char *name);

struct stats *get_current_stats(struct stats_type *type, const char *dev);
void stats_set(struct stats *s, const char *key, unsigned long long val);
void stats_inc(struct stats *s, const char *key, unsigned long long val);

#endif
