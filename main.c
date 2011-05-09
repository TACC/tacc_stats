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
#include <time.h>
#include <sys/file.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <semaphore.h>
#include "stats.h"
#include "stats_file.h"
#include "trace.h"
#include "schema.h"
#include "pscanf.h"

const char *stats_dir_path = "/var/log/tacc_stats"; /* XXX */
static const char *stats_sem_path = "/tacc_stats_sem";
static sem_t *stats_sem = NULL;
static int stats_sem_timeout = 30;

time_t current_time;
char current_jobid[80] = "0";
int nr_cpus;

static void alarm_handler(int sig)
{
}

static int stats_lock(void)
{
  int rc = 0;
  void (*prev_alarm_handler)(int) = SIG_ERR;

  if (stats_sem == NULL)
    stats_sem = sem_open(stats_sem_path, O_CREAT, 0600, 1);

  if (stats_sem == SEM_FAILED) {
    ERROR("cannot open `%s': %m\n", stats_sem_path);
    rc = -1;
    goto out;
  }

  prev_alarm_handler = signal(SIGALRM, &alarm_handler);
  alarm(stats_sem_timeout);

  if (sem_wait(stats_sem) < 0) {
    if (errno == EINTR)
      errno = ETIMEDOUT;
    ERROR("cannot lock `%s': %m\n", stats_sem_path);
    rc = -1;
    goto out;
  }

 out:
  alarm(0);
  if (prev_alarm_handler != SIG_ERR)
    signal(SIGALRM, prev_alarm_handler);

  return rc;
}

static void stats_unlock(void)
{
  if (stats_sem == NULL || stats_sem == SEM_FAILED)
    return;

  if (sem_post(stats_sem) < 0)
    ERROR("cannot unlock `%s': %m\n", stats_sem_path);
}

static void usage(void)
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
  int rc = 0;
  const char *mark = NULL;
  char *stats_file_path = NULL; /* <stats_dir_path>/current */

  struct option opts[] = {
    { "help", 0, 0, 'h' },
    { "mark", 0, 0, 'm' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "hm:", opts, 0)) != -1) {
    switch (c) {
    case 'h':
      usage();
      exit(0);
    case 'm':
      mark = optarg;
      break;
    case '?':
      fprintf(stderr, "Try `%s --help' for more information.\n", program_invocation_short_name);
      exit(1);
    }
  }

  umask(022);

  if (!(optind < argc))
    FATAL("must specify a command\n");

  asprintf(&stats_file_path, "%s/current", stats_dir_path);
  if (stats_file_path == NULL)
    FATAL("cannot create path: %m\n");

  const char *cmd_str = argv[optind];
  char **arg_list = argv + optind + 1;
  size_t arg_count = argc - optind - 1;

  enum {
    cmd_begin,
    cmd_collect,
    cmd_end,
    cmd_rotate,
  } cmd;

  if (strcmp(cmd_str, "begin") == 0)
    cmd = cmd_begin;
  else if (strcmp(cmd_str, "collect") == 0)
    cmd = cmd_collect;
  else if (strcmp(cmd_str, "end") == 0)
    cmd = cmd_end;
  else if (strcmp(cmd_str, "rotate") == 0)
    cmd = cmd_rotate;
  else
    FATAL("invalid command `%s'\n", cmd_str);

  if (stats_lock() < 0)
    FATAL("cannot acquire lock\n");

  if (cmd == cmd_rotate) {
    if (unlink(stats_file_path) < 0 && errno != ENOENT) {
        ERROR("cannot unlink `%s': %m\n", stats_file_path);
        rc = 1;
    }
    goto out;
  }

  current_time = time(0);
  pscanf(JOBID_PATH, "%79s", current_jobid);
  nr_cpus = sysconf(_SC_NPROCESSORS_ONLN);

  struct stats_file sf;
  if (stats_file_open(&sf, stats_file_path) < 0) {
    rc = 1;
    goto out;
  }

  int enable_all = 0;
  int select_all = cmd != cmd_collect || arg_count == 0;

  if (sf.sf_empty) {
    time_t epoch = time(NULL);
    char *link_path = NULL;
    asprintf(&link_path, "%s/%ld", stats_dir_path, epoch);
    if (link_path == NULL) {
      ERROR("cannot create path: %m\n");
    } else if (link(stats_file_path, link_path) < 0) {
      ERROR("cannot link `%s' to `%s': %m\n", stats_file_path, link_path);
    }
    free(link_path);

    enable_all = 1;
    select_all = 1;
  }

  size_t i;
  struct stats_type *type;

  if (cmd == cmd_collect) {
    /* If arg_count is zero then we select all below. */
    for (i = 0; i < arg_count; i++) {
      type = name_to_type(arg_list[i]);
      if (type == NULL) {
        ERROR("unknown type `%s'\n", arg_list[i]);
        continue;
      }
      type->st_selected = 1;
    }
  }

  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (enable_all)
      type->st_enabled = 1;

    if (!type->st_enabled)
      continue;

    if (stats_type_init(type) < 0) {
      type->st_enabled = 0;
      continue;
    }

    if (select_all)
      type->st_selected = 1;

    if (cmd == cmd_begin && type->st_begin != NULL)
      (*type->st_begin)(type);

    if (type->st_enabled && type->st_selected)
      (*type->st_collect)(type);
  }

  if (mark != NULL)
    stats_file_mark(&sf, "%s", mark);
  else if (cmd == cmd_begin || cmd == cmd_end)
    /* On begin set mark to "begin JOBID", and similar for end. */
    stats_file_mark(&sf, "%s %s", cmd_str, arg_count > 0 ? arg_list[0] : "-");

  if (stats_file_close(&sf) < 0)
    rc = 1;

 out:
  stats_unlock();
  return rc;
}
