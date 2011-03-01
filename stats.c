#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stats.h"
#include "trace.h"
#include "dict.h"

#define X(t) extern struct stats_type t##_TYPE;
#include "stats.x"
#undef X

struct stats_type *stats_type[] = {
#define X(t) [t] = &t##_TYPE,
#include "stats.x"
#undef X
};

size_t nr_stats_types = sizeof(stats_type) / sizeof(stats_type[0]);

void read_stats(void)
{
  size_t i, j;

  for (i = 0; i < nr_stats_types; i++) {
    struct stats_type *type = stats_type[i];
    for (j = 0; ; j++) {
      void (*read)(struct stats_type *) = type->st_read[j];
      if (read == NULL)
        break;
      (*read)(type);
    }
  }
}

struct stats *get_current_stats(struct stats_type *type, const char *id)
{
  if (id == NULL)
    id = "-";

  TRACE("get_current_stats %s %s\n", type->st_name, id);

  return (struct stats *) id;
}

void stats_set(struct stats *st, char *key, unsigned long long val)
{
  const char *id = (const char*) st;
  TRACE("stats_set %s %s %llu\n", id, key, val);
}

void stats_inc(struct stats *st, char *key, unsigned long long val)
{
  const char *id = (const char*) st;
  TRACE("stats_inc %s %s %llu\n", id, key, val);
}

void stats_set_unit(struct stats *st, char *key, unsigned long long val, const char *unit)
{
  const char *id = (const char*) st;
  unsigned long long mult = 1;

  if (strcasecmp(unit, "KB") == 0)
    mult = 1ULL << 10;
  else if (strcasecmp(unit, "MB") == 0)
    mult = 1ULL << 20;
  else if (strcasecmp(unit, "GB") == 0)
    mult = 1ULL << 30;
  else if (strcasecmp(unit, "TB") == 0)
    mult = 1ULL << 40;
  else if (strlen(unit) != 0)
    ERROR("unknown unit `%s'\n", unit);

  TRACE("stats_set_unit %s %s %llu %s %llu\n", id, key, val, unit, mult);
}
