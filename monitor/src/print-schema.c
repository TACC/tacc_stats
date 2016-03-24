#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <getopt.h>
#include <malloc.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>
#include "string1.h"
#include "stats.h"
#include "trace.h"
#include "pscanf.h"

#define SF_SCHEMA_CHAR '!'

static void usage(void)
{
  fprintf(stderr,
          "Usage: %s [OPTION]... [FILE]\n"
          "Dump schema to stdout or FILE.\n"
          "\n"
          "Mandatory arguments to long options are mandatory for short options too.\n"
          "  -h, --help         display this help and exit\n"
          /* "  -l, --list-types ...\n" */
          /* describe */
          ,
          program_invocation_short_name);
}

int main(int argc, char *argv[])
{
  const char *schema_path = "/dev/sdtout";
  FILE *schema_file = stdout;

  struct option opts[] = {
    { "help", 0, 0, 'h' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "h", opts, 0)) != -1) {
    switch (c) {
    case 'h':
      usage();
      exit(0);
    case '?':
      fprintf(stderr, "Try `%s --help' for more information.\n", program_invocation_short_name);
      exit(1);
    }
  }

  umask(022);

  if (optind < argc) {
    schema_path = argv[optind];
    schema_file = fopen(schema_path, "w");
  }

  if (schema_file == NULL)
    FATAL("cannot open `%s': %m\n", schema_path);

  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL)
    fprintf(schema_file, "%s%s\n", type->st_name, type->st_schema_def);

  fclose(schema_file);

  return 0;
}
