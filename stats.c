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

size_t nr_stats_types = sizeof(type_table) / sizeof(type_table[0]);

static void init(void) __attribute__((constructor));
static void init(void)
{
  current_time = time(0);

  nr_cpus = sysconf(_SC_NPROCESSORS_ONLN);
  TRACE("nr_cpus %d\n", nr_cpus);

  /* Initialize types. */
  size_t i;

  for (i = 0; i < nr_stats_types; i++) {
    struct stats_type *type = type_table[i];
    if (dict_init(&type->st_current_dict, 0) < 0)
      /* XXX */;
  }
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

  val = calloc(type->st_schema_len, sizeof(*stats->s_val));
  if (val == NULL && type->st_schema_len != 0)
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
  struct dict_entry *ent;
  hash_t hash;

  if (dev == NULL)
    dev = "-";

  TRACE("get_current_stats %s %s\n", type->st_name, dev);

  hash = dict_strhash(dev);
  ent = dict_entry_ref(&type->st_current_dict, hash, dev);
  if (ent->d_key != NULL)
    return (struct stats *) ent->d_key - 1;

  stats = stats_create(type, dev);
  if (stats == NULL) {
    ERROR("stats_create: %m\n");
    return NULL;
  }

  if (dict_entry_set(&type->st_current_dict, ent, hash, stats->s_dev) < 0) {
    ERROR("dict_entry_set: %m\n");
    stats_free(stats);
    return NULL;
  }

  return stats;
}

void stats_set(struct stats *stats, const char *key, unsigned long long val)
{
  char *sk;
  struct schema_entry *se;

  TRACE("%s %s %s %llu\n",
        stats->s_type->st_name, stats->s_dev, key, val);

  sk = dict_ref(&stats->s_type->st_schema_dict, key);
  if (sk == NULL)
    return;

  se = (struct schema_entry *) sk - 1;

  stats->s_val[se->se_index] = val;
}

void stats_inc(struct stats *stats, const char *key, unsigned long long val)
{
  char *sk;
  struct schema_entry *se;

  TRACE("%s %s %s %llu\n",
        stats->s_type->st_name, stats->s_dev, key, val);

  sk = dict_ref(&stats->s_type->st_schema_dict, key);
  if (sk == NULL)
    return;

  se = (struct schema_entry *) sk - 1;

  stats->s_val[se->se_index] = val;
}

void stats_type_collect(struct stats_type *type)
{
  void (*collect)(struct stats_type *) = type->st_collect;

  if (collect != NULL)
    (*collect)(type);
}
