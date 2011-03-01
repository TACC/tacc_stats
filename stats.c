#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stats.h"
#include "stats-type.h"
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

struct stats *get_current_stats(int type, const char *id)
{
  struct stats_type *stats_type = stats_type[type];

  if (id == NULL)
  /* TRACE("get_current_stats %s %s\n", st_name[type], id); */

  ref = dict_search(.st_current_dict, id);
  if (*ref == id) {
  }

  return ((struct stats *) *ref) - 1;
}

