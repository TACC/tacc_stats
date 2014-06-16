#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stats.h"
#include "trace.h"
#include "dict.h"
#include "schema.h"

/* This first define statement uses the stats.x text file. The 
 * pre-processor includes this file which contains text that is 
 * formatted in X(t) where t is the type you want to collect. When
 * the file is scanned again by the pre-processor these X() functions
 * are re-defined by the #define statement to create structs. For
 * example 'X(cpu)' in the stats.x file would turn into
 * 'extern struct stats_type cpu_stats_type;' in this file.
 * Note that these structs are define in their respective files, 
 * for example 'mem_stats_type' is define in mem.c and is referenced
 * by this 'extern struct stats_type mem_stats_type'.*/
#define X(t) extern struct stats_type t##_stats_type;
#include "stats.x"
#undef X

/* This define statment works in conjunction with the above define
 * statement. The above define statment creates the structs and
 * this will create a struct that holds the location of all the 
 * previous created structs. So, 'X(cpu)' in stats.x will become
 * '&cpu_stats_type,' in this struct def. */
struct stats_type *type_table[] = {
#define X(t) &t##_stats_type,
#include "stats.x"
#undef X
};

static size_t nr_stats_types = sizeof(type_table) / sizeof(type_table[0]);

static void stats_destroy(struct stats *stats);

/* init the type */
int stats_type_init(struct stats_type *st)
{
  TRACE("type %s, schema_def `%s'\n", st->st_name, st->st_schema_def);

  // enable/disable performance counters
  if ( ( strcmp(st->st_name,"amd64_pmc") == 0 ) ||
       ( strcmp(st->st_name,"intel_pmc3") == 0 ) ||
       ( strcmp(st->st_name,"intel_uncore") == 0 ) ) { 

    // determine if running on intel or amd
    char line[256];
    FILE *cpuinfo;
    cpuinfo = fopen("/proc/cpuinfo", "r");
    char * is_intel = 0;
    if ( cpuinfo != NULL ) {

      while( fgets( line, sizeof line, cpuinfo) != NULL ) { 
        is_intel = strstr( line, "GenuineIntel" );
        if (is_intel) break;  // intel
      }   
      fclose(cpuinfo);
    
      // set correct performance counters based on architecture
      if ( is_intel && ( strcmp(st->st_name,"amd64_pmc") == 0 ) ) 
        return -1; // found intel so turn off amd pmc
      if ( (!is_intel) && ( ( strcmp(st->st_name,"intel_pmc3") == 0 ) ||  
                            ( strcmp(st->st_name,"intel_uncore") == 0 ) ) ) 
        return -1; // found amd so turn off intel pmc

    } else {

      TRACE("Could not open /proc/cpuinfo to determine intel or amd\n");

    }

  }

  // init the schema
  if (schema_init(&st->st_schema, st->st_schema_def) < 0)
    return -1;

  // init the dict
  if (dict_init(&st->st_current_dict, 0) < 0)
    return -1;

  return 0;
}

void key_stats_destroy(void *key)
{
  stats_destroy(key_to_stats(key));
}

void stats_type_destroy(struct stats_type *st)
{
  //extern char _edata[]; /* XXX */
  /* modified by charngda */
  /* don't use the _edata hack */
  //if (st->st_schema_def >= _edata) {
  if (st->st_schema_def != st->orig_st_schema_def) {
    free(st->st_schema_def);
    st->st_schema_def = st->orig_st_schema_def;
    //st->st_schema_def = NULL;
  }

  schema_destroy(&st->st_schema);
  dict_destroy(&st->st_current_dict, &key_stats_destroy);
}

struct stats_type *stats_type_get(const char *name)
{
  size_t begin = 0, end = nr_stats_types;

  while (begin < end) {
    size_t mid = begin + (end - begin) / 2;
    struct stats_type *type = type_table[mid];

    int cmp = strcmp(name, type->st_name);
    if (cmp < 0)
      end = mid;
    else if (cmp > 0)
      begin = mid + 1;
    else
      return type;
  }

  return NULL;
}

// Return the struct address for each type that is defined in stats.x
// This function is usually used in a loop to go through all the stats.
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

static void stats_destroy(struct stats *stats)
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
    stats_destroy(stats);
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