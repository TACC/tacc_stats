#ifndef _STATS_H_
#define _STATS_H_
#include "dict.h"

enum {
#define X(t) t ,
#include "stats.x"
#undef X
};

struct stats {
  /* Type? */
  struct dict st_dict;
  char st_id[];
};

struct stats_type {
  char *st_name;
  void (**st_read)(void);
  char **st_print_schema;
  struct dict st_current_dict;
};

struct stats *get_current_stats(int type, const char *id);
void stats_set(struct stats *s, char *key, unsigned long long val);
void stats_set_unit(struct stats *s, char *key, unsigned long long val, const char *unit);
void stats_inc(struct stats *s, char *key, unsigned long long val);

#endif
