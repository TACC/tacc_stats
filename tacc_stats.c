#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <getopt.h>
#include <signal.h>
#include <errno.h>
#include <ctype.h>
#include <malloc.h>
#include <sys/file.h>
#include <sys/types.h>
#include <sys/stat.h>
#include "stats.h"
#include "stats_file.h"
#include "trace.h"
#include "schema.h"

/* MOVEME */
#ifndef EPREFIX
#define EPREFIX "/usr/local"
#endif

const char *lock_path = "/var/run/tacc_stats_lock";
const char *stats_path = "/var/run/tacc_stats_current";
const char *helper_path = EPREFIX"/bin/tacc_stats_helper";
char *const helper_envp[] = { "TACC_STATS_PROGRAM="EPREFIX"/bin/tacc_stats", NULL };

int helper(const char *path, char *const argv[], char *const envp[]);

int lock_timeout = 30;
int lock_fd = -1;
FILE *stats_file = NULL;

static void lock_alrm_handler(int sig)
{
}

static int lock(void)
{
  int rc = 0;
  void (*prev_alrm_handler)(int) = SIG_ERR;

  if (lock_fd < 0)
    lock_fd = open(lock_path, O_WRONLY|O_CREAT, 0600);

  if (lock_fd < 0) {
    ERROR("cannot open `%s': %m\n", lock_path);
    rc = -1;
    goto out;
  }

  prev_alrm_handler = signal(SIGALRM, &lock_alrm_handler);
  alarm(lock_timeout);

  if (flock(lock_fd, LOCK_EX) < 0) {
    if (errno == EINTR)
      errno = ETIMEDOUT;
    ERROR("cannot lock `%s': %m\n", lock_path);
    rc = -1;
    goto out;
  }

 out:
  alarm(0);
  if (prev_alrm_handler != SIG_ERR)
    signal(SIGALRM, prev_alrm_handler);

  return rc;
}

static void unlock(void)
{
  if (flock(lock_fd, LOCK_UN) < 0)
    ERROR("cannot unlock `%s': %m\n", lock_path);
}

static int tacc_stats_collect(char **arg_list, size_t arg_count)
{
  int rc = -1;
  size_t i = 0;
  struct stats_type *type;

  if (stats_file == NULL) {
    stats_file = fopen(stats_path, "r+");
    if (stats_file == NULL) {
      if (errno == ENOENT)
        rc = 0; /* OK just exit. */
      else
        ERROR("cannot open `%s': %m\n", stats_path);
      goto out;
    }

    if (stats_file_rd_hdr(stats_file, stats_path) < 0) {
      ERROR("cannot read header from `%s'\n", stats_path);
      goto out;
    }
  }

  /* Select types in argument list. */
  for (i = 0; i < arg_count; i++) {
    type = name_to_type(arg_list[i]);
    if (type == NULL) {
      ERROR("unknown type `%s'\n", arg_list[i]);
      continue;
    }
    type->st_selected = 1;
  }

  /* If no arguments were given then select all. */
  if (arg_count == 0) {
    i = 0;
    while ((type = stats_type_for_each(&i)) != NULL)
      type->st_selected = 1;
  }

  fseek(stats_file, 0, SEEK_END);

  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (type->st_enabled && type->st_selected)
      (*type->st_collect)(type);
  }

  if (stats_file_wr_rec(stats_file, stats_path) < 0)
    goto out;

  rc = 0;
 out:
  return rc;
}

char *join(char **list, size_t count, const char *delim)
{
  size_t len = 0;
  char *str = NULL, *dest;
  const char *src;
  int i;

  if (count > 0)
    len = strlen(list[0]);

  for (i = 1; i < count; i++)
    len += strlen(delim) + strlen(list[i]);

  str = malloc(len + 1);
  if (str == NULL)
    goto out;

  dest = str;

  if (count > 0) {
    src = list[0];
    while (*src != 0)
      *(dest++) = *(src++);
  }

  for (i = 1; i < count; i++) {
    src = delim;
    while (*src != 0)
      *(dest++) = *(src++);
    src = list[i];
    while (*src != 0)
      *(dest++) = *(src++);
  }

  *dest = 0;
 out:
  return str;
}

static int tacc_stats_mark(char **arg_list, size_t arg_count)
{
  int rc = -1;
  char *str = NULL, *iter, *line;

  str = join(arg_list, arg_count, " ");
  if (str == NULL) {
    ERROR("%m\n");
    goto out;
  }

  if (stats_file == NULL)
    stats_file = fopen(stats_path, "r+");

  if (stats_file == NULL) {
    ERROR("cannot open `%s': %m\n", stats_path);
    goto out;
  }

  fseek(stats_file, 0, SEEK_END);
  /* TODO Check size of stat_file. */

  iter = str;
  while ((line = strsep(&str, "\n")) != NULL)
    if (stats_file_printf(stats_file, stats_path, "#%s\n", line) < 0)
      goto out;

  rc = 0;
 out:
  free(str);
  return rc;
}

static int tacc_stats_begin(char **arg_list, size_t arg_count)
{
  int rc = -1;
  char *const argv[] = { "tacc_stats_helper", "begin", NULL };
  if (helper(helper_path, argv, helper_envp) != 0)
    return -1;

  stats_file = fopen(stats_path, "r+");
  if (stats_file == NULL) {
    ERROR("cannot open `%s': %m\n", stats_path);
    goto out;
  }

  /* Enable the types specified in arg_list. */
  size_t i;
  struct stats_type *type;
  for (i = 0; i < arg_count; i++) {
    type = name_to_type(arg_list[i]);
    if (type == NULL) {
      ERROR("unknown type `%s'\n", arg_list[i]);
      continue;
    }
    type->st_enabled = 1;
  }

  /* If no arguments were given then enable all. */
  if (arg_count == 0) {
    i = 0;
    while ((type = stats_type_for_each(&i)) != NULL)
      type->st_enabled = 1;
  }

  /* Set schemas and fire begin callbacks where defined. */
  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (!type->st_enabled)
      continue;

    TRACE("type %s, schema_def `%s'\n", type->st_name, type->st_schema_def);
    if (stats_type_set_schema(type, type->st_schema_def) < 0) {
      type->st_enabled = 0;
      continue;
    }

    if (type->st_begin != NULL && (*type->st_begin)(type) < 0) {
      type->st_enabled = 0;
      continue;
    }
  }

  if (stats_file_wr_hdr(stats_file, stats_path) < 0) {
    ERROR("cannot write header to `%s'\n", stats_path);
    goto out;
  }

  if (tacc_stats_collect(NULL, 0) < 0)
    goto out;

  rc = 0;
 out:
  return rc;
}

static int tacc_stats_end(char **arg_list, size_t arg_count)
{
  tacc_stats_collect(arg_list, arg_count);

  if (stats_file != NULL) {
    fclose(stats_file);
    stats_file = NULL;
  }

  char *const argv[] = { "tacc_stats_helper", "end", NULL };
  if (helper(helper_path, argv, helper_envp) != 0)
    return -1;

  return 0;
}

typedef int (*cmd_handler_t)(char **, size_t);
cmd_handler_t get_cmd_handler(const char *cmd)
{
  /* XXX */
  if (strcmp(cmd, "begin") == 0)
    return &tacc_stats_begin;
  if (strcmp(cmd, "collect") == 0)
    return &tacc_stats_collect;
  if (strcmp(cmd, "end") == 0)
    return &tacc_stats_end;
  if (strcmp(cmd, "mark") == 0)
    return &tacc_stats_mark;
  return NULL;
}

static void usage(int rc)
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
  exit(rc);
}

int main(int argc, char *argv[])
{
  umask(022);

  struct option opts[] = {
    { "help", 0, 0, 'h' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "h", opts, 0)) != -1) {
    switch (c) {
    case 'h':
      usage(0);
    case '?':
      fprintf(stderr, "Try `%s --help' for more information.\n", program_invocation_short_name);
      exit(1);
    }
  }

  if (!(optind < argc))
    FATAL("must specify a command\n");

  const char *cmd = argv[optind];
  char **cmd_arg_list = argv + optind + 1;
  size_t cmd_arg_count = argc - optind - 1;
  cmd_handler_t cmd_handler = get_cmd_handler(cmd);

  if (cmd_handler == NULL)
    FATAL("invalid command `%s'\n", cmd);

  if (lock() < 0)
    FATAL("cannot acquire lock\n");

  int cmd_rc = (*cmd_handler)(cmd_arg_list, cmd_arg_count);
  TRACE("command `%s' returned %d\n", cmd, cmd_rc);

  if (stats_file != NULL && fclose(stats_file) < 0)
    ERROR("error closing `%s': %m\n", stats_path);

  unlock();

  return 0; /* XXX */
}
