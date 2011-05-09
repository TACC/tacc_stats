#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <limits.h>
#include "stats.h"
#include "trace.h"
#include "dict.h"
#include "schema.h"

time_t current_time;
int nr_cpus;

#define X(t) extern struct stats_type STATS_TYPE_##t;
#include "stats.x"
#undef X

struct stats_type *type_table[] = {
#define X(t) &STATS_TYPE_##t,
#include "stats.x"
#undef X
};

static size_t nr_stats_types = sizeof(type_table) / sizeof(type_table[0]);

static void init(void) __attribute__((constructor));
static void init(void)
{
  current_time = time(0);
  nr_cpus = sysconf(_SC_NPROCESSORS_ONLN);
}

int stats_type_init(struct stats_type *st)
{
  TRACE("type %s, schema_def `%s'\n", st->st_name, st->st_schema_def);

  if (schema_init(&st->st_schema, st->st_schema_def) < 0)
    return -1;

  if (dict_init(&st->st_current_dict, 0) < 0)
    return -1;

  return 0;
}

// static int name_to_type_cmp(const void *name, const void *memb)
// {
//   struct stats_type **type = (struct stats_type **) memb;

//   return strcmp(name, (*type)->st_name);
// }

struct stats_type *name_to_type(const char *name)
{
//   return bsearch(name, type_table,
//                  nr_stats_types, sizeof(type_table[0]),
//                  &name_to_type_cmp);
  int i;
  for (i = 0; i < nr_stats_types; i++) {
    if (strcmp(name, type_table[i]->st_name) == 0)
      return type_table[i];
  }

  return NULL;
}

struct stats_type *stats_type_for_each(size_t *i)
{
  struct stats_type *type = NULL;

  if (*i < nr_stats_types) {
    type = type_table[*i];
    (*i)++;
  }

  return type;
}

static struct stats *stats_create(struct stats_type *type, const char *dev)
{
  struct stats *stats = NULL;
  unsigned long long *val = NULL;

  stats = malloc(sizeof(*stats) + strlen(dev) + 1);
  if (stats == NULL)
    goto err;

  val = calloc(type->st_schema.sc_len, sizeof(*stats->s_val));
  if (val == NULL && type->st_schema.sc_len != 0)
    goto err;

  memset(stats, 0, sizeof(*stats));
  stats->s_type = type;
  stats->s_val = val;
  strcpy(stats->s_dev, dev);
  return stats;

 err:
  free(stats);
  free(val);
  return NULL;
}

static void stats_free(struct stats *stats)
{
  free(stats->s_val);
  free(stats);
}

struct stats *get_current_stats(struct stats_type *type, const char *dev)
{
  struct stats *stats = NULL;
  struct dict_entry *de;
  hash_t hash;

  if (dev == NULL)
    dev = "-";

  TRACE("get_current_stats %s %s\n", type->st_name, dev);

  hash = dict_strhash(dev);
  de = dict_entry_ref(&type->st_current_dict, hash, dev);
  if (de->d_key != NULL)
    return key_to_stats(de->d_key);

  stats = stats_create(type, dev);
  if (stats == NULL) {
    ERROR("stats_create: %m\n");
    return NULL;
  }

  if (dict_entry_set(&type->st_current_dict, de, hash, stats->s_dev) < 0) {
    ERROR("dict_entry_set: %m\n");
    stats_free(stats);
    return NULL;
  }

  return stats;
}

void stats_set(struct stats *stats, const char *key, unsigned long long val)
{
  int i = schema_ref(&stats->s_type->st_schema, key);

  TRACE("%s %s %s %llu %d\n",
        stats->s_type->st_name, stats->s_dev, key, val, i);

  if (i >= 0)
    stats->s_val[i] = val;
}

void stats_inc(struct stats *stats, const char *key, unsigned long long val)
{
  int i = schema_ref(&stats->s_type->st_schema, key);

  TRACE("%s %s %s %llu %d\n",
        stats->s_type->st_name, stats->s_dev, key, val, i);

  stats->s_val[i] = val;
}
