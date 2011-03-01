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

static void init_types(void) __attribute__((constructor));

static void init_types(void)
{
  size_t i;

  for (i = 0; i < nr_stats_types; i++) {
    struct stats_type *type = stats_type[i];
    if (dict_init(&type->st_current_dict, 0) < 0)
      /* XXX */;
  }
}

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

static struct stats *stats_create(struct stats_type *type, const char *id)
{
  struct stats *stats;

  stats = malloc(sizeof(*stats) + strlen(id) + 1);
  if (stats == NULL)
    return NULL;

  memset(stats, 0, sizeof(*stats));

  stats->st_type = type;

  if (dict_init(&stats->st_dict, 0) < 0) {
    free(stats);
    return NULL;
  }

  strcpy(stats->st_id, id);

  return stats;
}

static void stats_free(struct stats *stats)
{
  if (stats != NULL) {
    dict_destroy(&stats->st_dict);
    free(stats);
  }
}

struct stats *get_current_stats(struct stats_type *type, const char *id)
{
  struct stats *stats = NULL;
  struct dict_entry *ent;
  hash_t hash;

  if (id == NULL)
    id = "-";

  TRACE("get_current_stats %s %s\n", type->st_name, id);

  hash = dict_strhash(id);
  ent = dict_ref(&type->st_current_dict, hash, id);
  if (ent->d_key != NULL)
    return (struct stats *) ent->d_key - 1;

  stats = stats_create(type, id);
  if (stats == NULL) {
    ERROR("stats_create: %m\n");
    return NULL;
  }

  if (dict_set(&type->st_current_dict, ent, hash, stats->st_id) < 0) {
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

struct st_pair *stats_ref(struct stats *stats, char *key)
{
  struct st_pair *pair = NULL;
  struct dict_entry *ent;
  hash_t hash;

  hash = dict_strhash(key);
  ent = dict_ref(&stats->st_dict, hash, key);
  if (ent->d_key != NULL)
    return (struct st_pair *) (ent->d_key - sizeof(*pair));

  pair = malloc(sizeof(*pair) + strlen(key) + 1);
  if (pair == NULL) {
    ERROR("cannot create st_pair: %m\n");
    return NULL;
  }

  pair->p_val = 0;
  strcpy(pair->p_key, key);

  if (dict_set(&stats->st_dict, ent, hash, pair->p_key) < 0) {
    ERROR("dict_set: %m\n");
    free(pair);
    return NULL;
  }

  return pair;
}

void stats_set(struct stats *stats, char *key, unsigned long long val)
{
  struct st_pair *pair;

  TRACE("%s %s %s %s %llu\n",
        __func__, stats->st_type->st_name, stats->st_id, key, val);

  pair = stats_ref(stats, key);
  if (pair != NULL)
    pair->p_val = val;
}

void stats_inc(struct stats *stats, char *key, unsigned long long val)
{
  struct st_pair *pair;

  TRACE("%s %s %s %s %llu\n",
        __func__, stats->st_type->st_name, stats->st_id, key, val);

  pair = stats_ref(stats, key);
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

  TRACE("%s %s %s %s %llu %s %llu\n",
        __func__, stats->st_type->st_name, stats->st_id, key, val, unit, mult);

  stats_set(stats, key, val * mult);
}
