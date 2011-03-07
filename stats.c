#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <limits.h>
#include "stats.h"
#include "trace.h"
#include "dict.h"

#define X(T) extern struct stats_type T##_TYPE;
#include "stats.x"
#undef X

struct stats_type *type_table[] = {
#define X(T) &T##_TYPE,
#include "stats.x"
#undef X
};

time_t current_time;

size_t nr_stats_types = sizeof(type_table) / sizeof(type_table[0]);

static void init(void) __attribute__((constructor));
static void init(void)
{
  current_time = time(0);

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
  struct stats *stats;

  stats = malloc(sizeof(*stats) + strlen(dev) + 1);
  if (stats == NULL)
    return NULL;

  memset(stats, 0, sizeof(*stats));

  stats->s_type = type;

  if (dict_init(&stats->s_dict, 0) < 0) {
    free(stats);
    return NULL;
  }

  strcpy(stats->s_dev, dev);

  return stats;
}

static void stats_free(struct stats *stats)
{
  if (stats != NULL) {
    dict_destroy(&stats->s_dict);
    free(stats);
  }
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
  ent = dict_ref(&type->st_current_dict, hash, dev);
  if (ent->d_key != NULL)
    return (struct stats *) ent->d_key - 1;

  stats = stats_create(type, dev);
  if (stats == NULL) {
    ERROR("stats_create: %m\n");
    return NULL;
  }

  if (dict_set(&type->st_current_dict, ent, hash, stats->s_dev) < 0) {
    ERROR("dict_set: %m\n");
    stats_free(stats);
    return NULL;
  }

  return stats;
}

struct st_pair {
  unsigned long long p_val;
  char p_key[];
};

struct st_pair *stats_ref(struct stats *stats, const char *key, int create)
{
  struct st_pair *pair = NULL;
  struct dict_entry *ent;
  hash_t hash;

  hash = dict_strhash(key);
  ent = dict_ref(&stats->s_dict, hash, key);
  if (ent->d_key != NULL)
    return (struct st_pair *) (ent->d_key - sizeof(*pair));

  if (!create)
    return NULL;

  pair = malloc(sizeof(*pair) + strlen(key) + 1);
  if (pair == NULL) {
    ERROR("cannot create st_pair: %m\n");
    return NULL;
  }

  pair->p_val = 0;
  strcpy(pair->p_key, key);

  if (dict_set(&stats->s_dict, ent, hash, pair->p_key) < 0) {
    ERROR("dict_set: %m\n");
    free(pair);
    return NULL;
  }

  return pair;
}

void stats_set(struct stats *stats, char *key, unsigned long long val)
{
  struct st_pair *pair;

  TRACE("%s %s %s %llu\n",
        stats->s_type->st_name, stats->s_dev, key, val);

  pair = stats_ref(stats, key, 1);
  if (pair != NULL)
    pair->p_val = val;
}

unsigned long long stats_get(struct stats *stats, const char *key)
{
  struct st_pair *pair = stats_ref(stats, key, 0);
  if (pair == NULL)
    return 0;
  return pair->p_val;
}

void stats_inc(struct stats *stats, char *key, unsigned long long val)
{
  struct st_pair *pair;

  TRACE("%s %s %s %llu\n",
        stats->s_type->st_name, stats->s_dev, key, val);

  pair = stats_ref(stats, key, 1);
  if (pair != NULL)
    pair->p_val += val;
}

void stats_set_unit(struct stats *stats, char *key, unsigned long long val, const char *unit)
{
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

  TRACE("%s %s %s %llu %s %llu\n",
       stats->s_type->st_name, stats->s_dev, key, val, unit, mult);

  stats_set(stats, key, val * mult);
}

void stats_type_collect(struct stats_type *type)
{
  void (*collect)(struct stats_type *) = type->st_collect;

  if (collect != NULL)
    (*collect)(type);
}
