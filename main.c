#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <getopt.h>
#include <sys/types.h>
#include <sys/stat.h>
#include "stats.h"
#include "stats_file.h"
#include "trace.h"

const char *stats_dir_path = "/var/tacc_stats";

void usage(void)
{
  fprintf(stderr,
          "Usage: %s [OPTION]... [TYPE]...\n"
          "Collect statistics.\n"
          "\n"
          "Mandatory arguments to long options are mandatory for short options too.\n"
          "  -b, --begin=JOBID  begin collecting statistics for job JOBID.\n"
          "  -e, --end=JOBID    begin collecting statistics for job JOBID.\n"
          "  -f, --file=PATH    write statistics to file at PATH\n"
          "  -h, --help         display this help and exit\n"
          /* "  -l, --list-types ...\n" */

          ,
          program_invocation_short_name);
}

char *get_current_jobid(void)
{
  return "99999999"; /* XXX */
}

int main(int argc, char *argv[])
{
  FILE *stats_file = NULL;
  char *stats_file_path = NULL;
  const char *jobid = NULL;
  int begin = 0, end = 0;
  char **type_list = NULL;
  int type_count = 0;

  struct option opts[] = {
    { "begin", 1, 0, 'b' },
    { "end", 1, 0, 'e' },
    { "file", 1, 0, 'f' },
    { "help", 0, 0, 'h' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "b:e:f:h", opts, 0)) != -1) {
    switch (c) {
    case 'b':
      jobid = optarg;
      begin = 1;
      break;
    case 'e':
      jobid = optarg;
      end = 1;
      break;
    case 'f':
      stats_file_path = optarg;
      break;
    case 'h':
      usage();
      exit(0);
    case '?':
      fprintf(stderr, "Try `%s --help' for more information.\n", program_invocation_short_name);
      exit(1);
    }
  }

  type_list = argv + optind;
  type_count = argc - optind;

  /* TODO lockfile. */
  /* TODO Handle begin, end, change of job. */

  if (jobid == NULL)
    jobid = get_current_jobid();

  if (jobid == NULL)
    exit(0);

  if (stats_file_path == NULL)
    asprintf(&stats_file_path, "%s/%s", stats_dir_path, jobid);

  if (stats_file_path == NULL)
    FATAL("%m\n");

  stats_file = fopen(stats_file_path, "a+");
  if (stats_file == NULL)
    FATAL("cannot open `%s': %m\n", stats_file_path);

  struct stat stat_buf;
  if (fstat(fileno(stats_file), &stat_buf) < 0)
    FATAL("cannot stat `%s': %m\n", stats_file_path);

  if (stat_buf.st_size == 0) {
    /* The stats file is empty. */
    if (stats_file_wr_hdr(stats_file, stats_file_path) < 0)
      FATAL("cannot write header to stats file `%s'\n", stats_file_path);
  } else {
    if (stats_file_rd_hdr(stats_file, stats_file_path) < 0)
      FATAL("cannot read header from stats file `%s'\n", stats_file_path);
  }

  fflush(stats_file); /* Does fseek() do this for us? */
  fseek(stats_file, 0, SEEK_END);

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

  stats_file_wr_rec(stats_file, stats_file_path);

  if (fclose(stats_file) < 0)
    ERROR("error closing `%s': %m\n", stats_file_path);

  return 0;
}
