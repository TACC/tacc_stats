#define _GNU_SOURCE
#include <stdio.h>
#include <errno.h>
#include "stats.h"
#include "stats_file.h"
#include "trace.h"

int main(int argc, char *argv[])
{
  char **type_list = argv + 1;
  int type_count = argc - 1;

  if (type_count == 0) {
    /* Collect all. */
    struct stats_type *type;
    size_t i = 0;
    while ((type = stats_type_for_each(&i)) != NULL)
      stats_type_collect(type);
  } else {
    /* Collect only types in list. */
    /* TODO Protect against duplicates in type_list. */
    int i;
    for (i = 0; i < type_count; i++) {
      struct stats_type *type;
      type = name_to_type(type_list[i]);
      if (type == NULL) {
        ERROR("unknown type `%s'\n", type_list[i]);
        continue;
      }
      stats_type_collect(type);
    }
  }

  stats_file_wr_rec(stdout, "stdout");

  return 0;
}
