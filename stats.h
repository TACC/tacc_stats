#define _GNU_SOURCE
#ifndef _STATS_H_
#define _STATS_H_
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include "dict.h"
#include "trace.h"

#define TACC_STATS_PROGRAM "tacc_stats"
#define TACC_STATS_VERSION "1.0.0"

struct stats_type {
  unsigned int st_enabled:1, st_selected:1;
  char *st_name;
  int (*st_begin)(struct stats_type *type);
  int (*st_rd_config)(struct stats_type *type, char *str);
  void (*st_collect)(struct stats_type *type);
  char **st_schema;
  struct dict st_current_dict;
};

struct stats {
  struct stats_type *s_type;
  struct dict s_dict;
  char s_dev[];
};

extern time_t current_time;

struct stats_type *name_to_type(const char *name);
struct stats_type *stats_type_for_each(size_t *i);

void stats_type_collect(struct stats_type *type);
void stats_type_wr_stats(struct stats_type *type, FILE *file);

struct stats *get_current_stats(struct stats_type *type, const char *dev);
void stats_set(struct stats *s, const char *key, unsigned long long val);
void stats_set_unit(struct stats *s, const char *key, unsigned long long val, const char *unit);
void stats_inc(struct stats *s, const char *key, unsigned long long val);
unsigned long long stats_get(struct stats *stats, const char *key);

#endif
