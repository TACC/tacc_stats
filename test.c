#define _GNU_SOURCE
#include <stdio.h>
#include <errno.h>
#include "stats.h"
#include "trace.h"

int main(int argc, char *argv[])
{
  if (argc == 1) {
    collect_all();
  } else {
    int i;
    for (i = 1; i < argc; i++) {
      struct stats_type *type = name_to_type(argv[i]);
      if (type == NULL) {
        ERROR("unknown type `%s'\n", argv[i]);
        continue;
      }
      collect_type(type);
    }
  }

  print_all_stats(stdout, NULL);

  return 0;
}
