#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include "stats_aggr.h"
#include "trace.h"
#include "dict.h"

time_t begin, end, step = 600;
struct dict type_dict;
int nr_files;

int process(FILE *file, const char *path)
{
  if (begin <= 0 || end <= 0) {
    /* TODO Get begin, end from file. */
    FATAL("invalid begin or end time\n");
  }

  





  nr_files++;

  return 0;
}

int main(int argc, char *argv[])
{
  struct option opts[] = {
    { "begin", 1, NULL, 'b' },
    { "end", 1, NULL, 'e' },
    { "step", 1, NULL, 's' },
    { "help", 0, NULL, 'h' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "b:e:s:h", opts, 0)) != -1) {
    switch (c) {
    case 'b':
      begin = strtol(optarg, NULL, 0);
      break;
    case 'e':
      end = strtol(optarg, NULL, 0);
      break;
    case 's':
      step = strtol(optarg, NULL, 0);
      break;
    case 'h':
      usage(0);
    case '?':
      fprintf(stderr, "Try `%s --help' for more information.\n", program_invocation_short_name);
      exit(1);
    }
  }

  char **path_list = argv + optind;
  int path_count = argc - optind;

  dict_init(&type_dict, 0);

  if (path_count == 0)
    process(stdin, "-");

  int i;
  for (i = 0; i < path_count; i++) {
    char *path = path_list[i];
    if (strcmp(path, "-") == 0)
      path = "/dev/stdin";

    FILE *file = fopen(path, "r");
    if (file == NULL)
      FATAL("cannot open `%s': %m\n", path_list[i]);
    process(file, path_list[i]);
    fclose(file);
  }

  return 0;
}
