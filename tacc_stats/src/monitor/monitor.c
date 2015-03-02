#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <getopt.h>
#include <signal.h>
#include <malloc.h>
#include <errno.h>
#include <sys/time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/syslog.h>
#include "string1.h"
#include "stats.h"
#include "stats_buffer.h"
#include "trace.h"
#include "pscanf.h"

struct timeval tp;
double current_time;
char current_jobid[80] = "-";
int nr_cpus;

volatile sig_atomic_t g_begin_flag=0;
volatile sig_atomic_t g_new_flag = 1;

static void signal_handler(int sig) {
  switch(sig) {    
  case SIGHUP: 
    g_begin_flag  = 1;
    break;
  case SIGTERM: 
    g_new_flag  = 1;
    break;
  }
}

static void alarm_handler(int sig)
{
}

static void alarm_rotate(int sig)
{
  g_new_flag = 1;
}

#define BUF_SIZE 8

static int open_lock_timeout(const char *path, int timeout)
{
  int fd = -1;
  char buf[BUF_SIZE];
  struct sigaction alarm_action = {
    .sa_handler = &alarm_handler,
  };
  struct flock lock = {
    .l_type = F_WRLCK,
    .l_whence = SEEK_SET,
  };

  fd = open(path, O_CREAT|O_RDWR, 0600);
  if (fd < 0) {
    ERROR("cannot open `%s': %m\n", path);
    goto err;
  }

  if (sigaction(SIGALRM, &alarm_action, NULL) < 0) {
    ERROR("cannot set alarm handler: %m\n");
    goto err;
  }

  // Set timer to wait until signal SIGALRM is sent
  alarm(timeout);

  // Wait until any conflicting lock on the file is released. 
  // If alarm signal (SIGALRM) is caught then go to signal 
  // handler set in sigaction structure.
  if (fcntl(fd, F_SETLKW, &lock) < 0) {
    ERROR("cannot lock `%s': %m\n", path);
    goto err;
  }
  
  snprintf(buf, BUF_SIZE, "%ld\n", (long) getpid());
  if (write(fd, buf, strlen(buf)) != strlen(buf))
    syslog(LOG_INFO,"Writing to PID/lock file failed '%s'", STATS_LOCK_PATH);
  
  if (0) {
  err:
    if (fd >= 0)
      close(fd);
    fd = -1;
  }
  alarm(0);
  return fd;
}

static void usage(void)
{
  fprintf(stderr,
          "Usage: %s [OPTION]... [TYPE]...\n"
          "Collect statistics.\n"
          "\n"
          "Mandatory arguments to long options are mandatory for short options too.\n"
          "  -h, --help         display this help and exit\n"
#ifdef RMQ 
          "  -s [SERVER] or --server [SERVER]       Server to send data.\n"
          "  -p [PORT] or --port [PORT]         Port to use (5672 is the default).\n"
#endif
          /* "  -l, --list-types ...\n" */
          /* describe */
          ,
          program_invocation_short_name);
}

int main(int argc, char *argv[])
{

  /* Our process ID and Session ID */
  pid_t pid, sid;
  
  /* Fork off the parent process */
  pid = fork();
  if (pid < 0) {
    exit(EXIT_FAILURE);
  }
  /* If we got a good PID, then
     we can exit the parent process. */
  if (pid > 0) {
    exit(EXIT_SUCCESS);
  }
  /* Create a new SID for the child process */
  sid = setsid();
  if (sid < 0) {
    /* Log the failure */
    exit(EXIT_FAILURE);
  }
  /* Change the current working directory */
  if ((chdir("/")) < 0) {
    /* Log the failure */
    exit(EXIT_FAILURE);
  }

  /* Daemon Specific initialization */
  int lock_fd = -1;
  int lock_timeout = 30;
  char *host = NULL;
  char *port = NULL;
  int rc = 0;

  struct option opts[] = {
    { "help", 0, 0, 'h' },
    { "server", required_argument, 0, 's' },
    { "port", required_argument, 0, 'p' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "h:s:p:", opts, 0)) != -1) {
    switch (c) {
    case 'h':
      usage();
      exit(0);
    case 's':
      host = optarg;
      continue;
    case 'p':
      port = optarg;
      continue;
    case '?':
      fprintf(stderr, "Try `%s --help' for more information.\n", program_invocation_short_name);
    }
  }
  umask(022);

#ifdef RMQ
  if (host == NULL) {
    fprintf(stderr, "Must specify a RMQ server with -s [--server] argument.\n");
    rc = 1;
    goto out;
  }
  if (port == NULL) { 
    port = "5672";
  }
#endif

  /* monitord [types] */
  char **arg_list = argv + optind;
  size_t arg_count = argc - optind;

  enum {
    cmd_begin,
    cmd_collect,
    cmd_end,
  } cmd;

  // Ensures only one monitord is running at any time on a node
  lock_fd = open_lock_timeout(STATS_LOCK_PATH, lock_timeout);
  if (lock_fd < 0) {
    fprintf(stderr,"cannot acquire lock\n");
    exit(1);
  }

  nr_cpus = sysconf(_SC_NPROCESSORS_ONLN);

  /* Close out the standard file descriptors */
  close(STDIN_FILENO);
  close(STDOUT_FILENO);
  close(STDERR_FILENO);

  /* Set up signal for terminating daemon */
  signal(SIGHUP, signal_handler);
  signal(SIGTERM, signal_handler);

  int enable_all = 1;
  int select_all = (arg_count == 0);
  
  /* Collect is default and only
   changes when HUP signal is received. */
  cmd = cmd_collect;   

  syslog(LOG_INFO, 
	 "Starting tacc_stats monitoring daemon.\n");

  // Setup alarm to notify when to rotate (every 24hrs)
  struct sigaction alarm_action = {
    .sa_handler = &alarm_rotate,
  };
  if (sigaction(SIGALRM, &alarm_action, NULL) < 0) {
    ERROR("cannot set alarm rotate handler: %m\n");
    goto out;
  }
  // Set timer to wait until signal SIGALRM is sent
  alarm(86400);

  while(1) {

    /* HUP signal received.  Rotate jobid in or out */
    if (g_begin_flag) {
      if (strcmp(current_jobid,"-") == 0) 
	cmd = cmd_begin;
      else
	cmd = cmd_end;
      g_begin_flag = 0;
    }

    /* Open the data buffer */    
    struct stats_buffer sf;
    if (stats_buffer_open(&sf) < 0) {
      rc = 1;
      goto out;
    }
    
#ifdef RMQ
    sf.sf_host = host;
    sf.sf_port = port;
#endif

    // Get current time
    gettimeofday(&tp,NULL);
    current_time = tp.tv_sec+tp.tv_usec/1000000.0;

    size_t i;
    struct stats_type *type;
    
    /* Only selected types will be collected 
       If arg_count is zero then we select all below. */
    for (i = 0; i < arg_count; i++) {
      type = stats_type_get(arg_list[i]);
      if (type == NULL) {
	ERROR("unknown type `%s'\n", arg_list[i]);
	continue;
      }
      type->st_selected = 1;
    }

    /* Program every enabled type but collect only selected types */
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

    /* On begin set mark to "begin JOBID", and similar for end. */
    if (cmd == cmd_begin) {
      pscanf(JOBID_FILE_PATH, "%79s", current_jobid);
      syslog(LOG_INFO, 
	     "Starting tacc_stats monitoring daemon for jobid %s.\n",
	     current_jobid);
      stats_buffer_mark(&sf, "%s %s", "begin", current_jobid);      
    }
    else if (cmd == cmd_end) {
      syslog(LOG_INFO,
	     "Stopping tacc_stats monitoring daemon for jobid %s\n",
	     current_jobid);
      stats_buffer_mark(&sf, "%s %s", "end", current_jobid);      
    } 

    /* Send header at start.  Causes receiver to rotate files. */
    if (g_new_flag) {
      if (stats_wr_hdr(&sf) < 0) {
	fprintf(stderr,"rotate signal failed : %m\n");
	rc = 1;
      }
      g_new_flag = 0;
      // Set timer to wait until signal SIGALRM is sent (rotate every 24 hrs)
      alarm(86400);
    }
    
    /* Write data to buffer and ship off node */
    if (stats_buffer_write(&sf) < 0)
      rc = 1;
    
    /* Cleanup. */
    i = 0;
    while ((type = stats_type_for_each(&i)) != NULL)
      stats_type_destroy(type);
    
    if (cmd == cmd_end) strcpy(current_jobid, "-");
    cmd = cmd_collect;

    // Sleep for X seconds
    sleep(FREQUENCY);
  }

 out:
    return rc;
    
    exit(EXIT_SUCCESS);
}
