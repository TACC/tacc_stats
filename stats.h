#ifndef _STATS_H_
#define _STATS_H_
#include <stdlib.h>
#include "dict.h"

enum {
#define X(t) t ,
#include "stats.x"
#undef X
};

struct stats_type {
  char *st_name;
  void (**st_read)(struct stats_type *type);
  char **st_schema;
  struct dict st_current_dict;
};

struct stats {
  struct stats_type *st_type;
  struct dict st_dict;
  char st_id[];
};

void read_stats(void);

struct stats *get_current_stats(struct stats_type *type, const char *id);
void stats_set(struct stats *s, char *key, unsigned long long val);
void stats_set_unit(struct stats *s, char *key, unsigned long long val, const char *unit);
void stats_inc(struct stats *s, char *key, unsigned long long val);

#endif
