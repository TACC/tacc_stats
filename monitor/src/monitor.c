#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <getopt.h>
#include <signal.h>
#include <malloc.h>
#include <errno.h>
#include <sys/fcntl.h>
#include <sys/time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/syslog.h>
#include <sys/inotify.h>
#include "string1.h"
#include "stats.h"
#include "stats_buffer.h"
#include "trace.h"
#include "pscanf.h"

#define EVENT_SIZE  ( sizeof (struct inotify_event) )
#define EVENT_BUF_LEN     ( 1024 * ( EVENT_SIZE + 16 ) )

struct timeval tp;
double current_time;
char current_jobid[80] = "-";
char new_jobid[80] = "-";
int nr_cpus;

static volatile sig_atomic_t g_new_flag = 1;

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
          "  -s [SERVER] or --server [SERVER]       Server to send data.\n"
          "  -q [QUEUE] or --queue [QUEUE]      Queue to route data to on RMQ server. \n"
          "  -p [PORT] or --port [PORT]         Port to use (5672 is the default).\n"
          "  -f [FREQUENCY] or --frequency [FREQUENCY]  Frequency to sample (600 seconds is the default).\n"
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

  // This block will force begin to wait until initialization is complete
  sigset_t mask;
  sigemptyset(&mask);
  sigaddset(&mask, SIGHUP);
  sigaddset(&mask, SIGTERM);
  sigprocmask(SIG_BLOCK, &mask, NULL);

  /* Daemon Specific initialization */
  int lock_fd = -1;
  int lock_timeout = 30;
  char *host = NULL;
  char *queue = NULL;
  char *port = "5672";
  double frequency = 600;

  int rc = 0;
  
  // Ensures only one monitord is running at any time on a node
  lock_fd = open_lock_timeout(STATS_LOCK_PATH, lock_timeout);
  if (lock_fd < 0) {
    ERROR("cannot acquire lock\n");
    exit(EXIT_FAILURE);
  }

  struct option opts[] = {
    { "help", 0, 0, 'h' },
    { "server", required_argument, 0, 's' },
    { "queue", required_argument, 0, 'q' },
    { "port", required_argument, 0, 'p' },
    { "frequency", required_argument, 0, 'f' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "h:s:q:p:f:", opts, 0)) != -1) {
    switch (c) {
    case 'h':
      usage();
      exit(0);
    case 's':
      host = optarg;
      continue;
    case 'q':
      queue = optarg;
      continue;
    case 'p':
      port = optarg;
      continue;
    case 'f':
      frequency = atof(optarg);
      continue;
    case '?':
      fprintf(stderr, "Try `%s --help' for more information.\n", program_invocation_short_name);
    }
  }
  umask(022);

  if (host == NULL || queue == NULL) {
    if (host == NULL)
      fprintf(stderr, "Must specify a RMQ server with -s [--server] argument.\n");
    if (queue == NULL)
      fprintf(stderr, "Must specify a RMQ queue with -q [--queue] argument.\n");
    rc = -1;
    goto out;
  }

  enum {
    cmd_reset,
    cmd_collect,
  } cmd;

  nr_cpus = sysconf(_SC_NPROCESSORS_ONLN);

  /* Close out the standard file descriptors */
  close(STDIN_FILENO);
  close(STDOUT_FILENO);
  close(STDERR_FILENO);

  int enable_all = 1;
  
  /* Collect is default and only
   changes when HUP signal is received. */
  cmd = cmd_collect;   

  syslog(LOG_INFO, "Start tacc_stats service. Direct data to host %s in queue %s with frequency %f\n", 
	 host, queue, frequency);

  // Setup rotation handler alarm_action
  struct sigaction alarm_action = {
    .sa_handler = &alarm_rotate,
  };
  // SIGALRM for auto rotation
  if (sigaction(SIGALRM, &alarm_action, NULL) < 0) {
    ERROR("cannot set alarm rotate handler: %m\n");
    rc = -1;
    goto out;
  }
  // SIGTERM for manual rotation
  if (sigaction(SIGTERM, &alarm_action, NULL) < 0) {
    ERROR("cannot set manual rotation handler: %m\n");
    rc = -1;
    goto out;
  }
  // Set timer to send SIGALRM  (every 24hrs)
  alarm(86400);
  
  FILE *jobfd = fopen(JOBID_FILE_PATH, "w+");
  if (jobfd == NULL) {
    ERROR("cannot open %s: %m\n", JOBID_FILE_PATH);
    goto out;
  }
  char *dash = "-\n";
  if (fwrite(dash, sizeof(char), 2, jobfd) < 2) {
    ERROR("cannot write to %s: %m\n", JOBID_FILE_PATH);
    goto out;
  }
  fclose(jobfd);

  int ifd, wd;
  ifd = inotify_init1(IN_NONBLOCK);
  if (ifd < 0) {
    ERROR("inotify_init failed: %m\n");
    rc = -1;
    goto out;
  }

  wd = inotify_add_watch(ifd, JOBID_FILE_PATH, IN_CLOSE_WRITE | IN_DELETE_SELF);
  if ( wd < 0) {
    ERROR("inotify failed: %m\n");  
    rc = -1;
    goto out;
  }
  
  char buffer[EVENT_BUF_LEN];
  ///////////////////////
  // START OF MAIN LOOP//
  ///////////////////////
  struct timespec timeout = {.tv_sec = (time_t)3600, .tv_nsec = 0};    
  fd_set descriptors;
  while(1) {
    // Block rotate until sample is complete
    sigprocmask(SIG_BLOCK, &mask, NULL);

    read(ifd, buffer, EVENT_BUF_LEN);

    // If Job ID file was deleted recreate and watch
    struct inotify_event *event = ( struct inotify_event * ) &buffer[0];
    if (event->mask & IN_DELETE_SELF) {
	syslog(LOG_INFO, "Job ID file was deleted.  Write a new one and watch.");
	FILE *jobfd = fopen(JOBID_FILE_PATH, "w+");
	fwrite(current_jobid, sizeof(char), sizeof(current_jobid), jobfd);
	fclose(jobfd);
	wd = inotify_add_watch(ifd, JOBID_FILE_PATH, IN_CLOSE_WRITE | IN_DELETE_SELF);
	if ( wd < 0) {
	  TRACE("inotify failed: %m\n");  
	}
    }

    FD_ZERO(&descriptors);
    FD_SET(ifd, &descriptors);
    pscanf(JOBID_FILE_PATH, "%79s", new_jobid);

    // Open the data buffer
    struct stats_buffer sf;
    if (stats_buffer_open(&sf, host, port, queue) < 0)
      TRACE("Failed opening data buffer : %m\n");

    if (strcmp(current_jobid, new_jobid) != 0) {            
      if (strcmp(new_jobid,"-") != 0) {          
	syslog(LOG_INFO, "Loading jobid %s from %s\n", new_jobid, JOBID_FILE_PATH);	
	stats_buffer_mark(&sf, "begin %s", new_jobid);
	strcpy(current_jobid, new_jobid);
	timeout.tv_sec = frequency; 
	timeout.tv_nsec = 0;    
      }
      else {
	syslog(LOG_INFO, "Unloading jobid %s from %s\n", current_jobid, JOBID_FILE_PATH);	
	stats_buffer_mark(&sf, "end %s", current_jobid);
	timeout.tv_sec = 3600; 
	timeout.tv_nsec = 0;    
      }
      cmd = cmd_reset;
    }
    // Get current time
    gettimeofday(&tp,NULL);
    current_time = tp.tv_sec+tp.tv_usec/1000000.0;

    size_t i;
    struct stats_type *type;
    
    // collect every enabled type 
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
	
      if ((g_new_flag || cmd == cmd_reset) && type->st_begin != NULL)
	(*type->st_begin)(type);

      if (type->st_enabled > 0)
	(*type->st_collect)(type);
    }

    enable_all = 0;

    // Send header at start.  Causes receiver to rotate files.
    if (g_new_flag) {
      if (stats_wr_hdr(&sf) < 0) {
	ERROR("Rotate signal failed : %m\n");
	syslog(LOG_INFO, "Sending signal to rotate stats file on host\n");
      }
      g_new_flag = 0;
      // Set timer to wait until signal SIGALRM is sent (rotate every 24 hrs)
      alarm(86400);
    }

    // Write data to buffer and ship off node
    if (stats_buffer_write(&sf) < 0)
      ERROR("Buffer write and send failed failed : %m\n");
    stats_buffer_close(&sf);

    // Cleanup
    i = 0;
    while ((type = stats_type_for_each(&i)) != NULL)
      stats_type_destroy(type);
    cmd = cmd_collect;

    strcpy(current_jobid, new_jobid);      
    sigprocmask(SIG_UNBLOCK, &mask, NULL);

    // Sleep for timeout
    pselect(FD_SETSIZE, &descriptors, NULL, NULL, &timeout, NULL);
  }

 out:
  inotify_rm_watch(ifd, wd);
  return rc;   
}
