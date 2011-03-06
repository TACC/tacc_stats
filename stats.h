#define _GNU_SOURCE
#ifndef _STATS_H_
#define _STATS_H_
#include <stdlib.h>
#include <stdio.h>
#include "dict.h"
#include "trace.h"

#define TACC_STATS_PROGRAM "tacc_stats"
#define TACC_STATS_VERSION "1.0.0"

struct stats_type {
  char *st_name;
  int (*st_config)(struct stats_type *type, char *str);
  void (*st_collect)(struct stats_type *type);
  char **st_schema;
  struct dict st_current_dict;
};

struct stats {
  struct stats_type *st_type;
  struct dict st_dict;
  char st_id[];
};

struct stats_type *name_to_type(const char *name);

void collect_all(void);
void collect_type(struct stats_type *type);
void print_all_stats(FILE *file, const char *prefix);
int tacc_stats_config(char *str);

static inline int stats_type_config(struct stats_type *type, char *str)
{
  if (type->st_config == NULL) {
    ERROR("type `%s' has no config method\n", type->st_name); /* XXX */
    return -1;
  }

  return (*type->st_config)(type, str);
}

static inline int stats_type_set_schema(struct stats_type *type, char *str)
{
  /* TODO */
  return 0;
}

static inline int stats_type_set_devices(struct stats_type *type, char *str)
{
  /* TODO */
  return 0;
}

struct stats *get_current_stats(struct stats_type *type, const char *id);
void stats_set(struct stats *s, char *key, unsigned long long val);
void stats_set_unit(struct stats *s, char *key, unsigned long long val, const char *unit);
void stats_inc(struct stats *s, char *key, unsigned long long val);

#endif
