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
#include "readstr.h"

void usage(void)
{
  fprintf(stderr,
          "Usage: %s [OPTION]... [TYPE]...\n"
          "Collect statistics.\n"
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
  const char *lock_file_path = "/var/run/tacc_stats_lock";
  const char *stats_file_path = "/var/run/tacc_stats_current";
  const char *jobid_file_path = "/var/run/TACC_jobid";
  int lock_file_fd = -1;
  FILE *stats_file = NULL;
  char **type_list = NULL;
  size_t type_count = 0;
  const char *jobid = NULL;

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

  type_list = argv + optind;
  type_count = argc - optind;

  lock_file_fd = open(lock_file_path, O_WRONLY|O_CREAT, 0600);
  if (lock_file_fd < 0)
    FATAL("cannot open `%s': %m\n", lock_file_path);

  struct flock lock = {
    .l_type = F_WRLCK,
    .l_start = SEEK_SET,
  };

  if (fcntl(lock_file_fd, F_SETLK, &lock) < 0)
    FATAL("cannot lock `%s': %m\n", lock_file_path);

  stats_file = fopen(stats_file_path, "r+");
  if (stats_file == NULL) {
    if (errno == ENOENT)
      exit(0); /* OK just exit. */
    FATAL("cannot open `%s': %m\n", stats_file_path);
  }

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

  jobid = readstr(jobid_file_path);
  stats_file_wr_rec(stats_file, stats_file_path, jobid);

  if (fclose(stats_file) < 0)
    ERROR("error closing `%s': %m\n", stats_file_path);

  return 0;
}
