#define _GNU_SOURCE
#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <time.h>
#include "stats.h"
#include "trace.h"

int main(int argc, char *argv[])
{
  while (1) {
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

    printf("%ld\n", time(0));
    print_all_stats(stdout, NULL);
    printf("\n");
    fflush(stdout);

    sleep(10);
  }

  return 0;
}
