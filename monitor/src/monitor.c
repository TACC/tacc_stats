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
#include <ev.h>
#include "daemonize.h"
#include "string1.h"
#include "stats.h"
#include "stats_buffer.h"
#include "trace.h"
#include "pscanf.h"

static char *app_name = NULL;
static char *conf_file_name = NULL;
static FILE *log_stream = NULL;

static char *server = NULL;
static char *queue  = "default";
static char *port   = "5672";

static double freq = 300;

static ev_timer sample_timer;
static ev_timer rotate_timer;

char jobid[80] = "-";

int nr_cpus;
int n_pmcs;
processor_t processor = 0;

int read_conf_file()
{
  FILE *conf_file_fd = NULL;
  int ret = -1;

  if (conf_file_name == NULL) return 0;

  conf_file_fd = fopen(conf_file_name, "r");

  if (conf_file_fd == NULL) {
    fprintf(log_stream, "Can not open config file: %s, error: %s",
	    conf_file_name, strerror(errno));
    return -1;
  }

  char *line_buf = NULL;
  size_t line_buf_size = 0;
  while(getline(&line_buf, &line_buf_size, conf_file_fd) >= 0) {
    char *line = line_buf;
    char *key = strsep(&line, " :\t=");
    if (key == NULL || line == NULL)
      continue;
    
    while (*line  == ' ') line++;
    if (strcmp(key, "server") == 0) { 
      line[strlen(line) - 1] = '\0';
      server = strdup(line);
      fprintf(log_stream, "%s: Setting server to %s based on file %s\n",
	      app_name, server, conf_file_name);
    }   
    if (strcmp(key, "queue") == 0) { 
      line[strlen(line) - 1] = '\0';
      queue = strdup(line);
      fprintf(log_stream, "%s: Setting queue to %s based on file %s\n",
	      app_name, queue, conf_file_name);
    }
    if (strcmp(key, "port") == 0) {
      line[strlen(line) - 1] = '\0';
      port = strdup(line);
      fprintf(log_stream, "%s: Setting server port to %s based on file %s\n",
	      app_name, port, conf_file_name);
    }
    if (strcmp(key, "frequency") == 0) {  
      if (sscanf(line, "%lf", &freq) == 1)
	fprintf(log_stream, "%s: Setting frequency to %f based on file %s\n",
		app_name, freq, conf_file_name);
    }
  }

  fclose(conf_file_fd);

  return ret;
}

static void send_stats_buffer(struct stats_buffer *sf) {

  size_t i;
  struct stats_type *type;

  // collect every enabled type 
  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL) {
    /*
    if (stats_type_init(type) < 0) {
      type->st_enabled = 0;
      continue;
    }
    */
    if (type->st_enabled)
      (*type->st_collect)(type);
  }

  // Write data to buffer and ship off node
  if (stats_buffer_write(sf) < 0)
    ERROR("Buffer write and send failed failed : %m\n");

  // Cleanup
  /*
  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL)
    stats_type_destroy(type);    
  */
}

/* Send header with data based on rotate timer interval */
static void rotate_timer_cb(struct ev_loop *loop, ev_timer *w, int revents) 
{
  pscanf(JOBID_FILE_PATH, "%79s", jobid);  

  struct stats_buffer sf;
  if (stats_buffer_open(&sf, server, port, queue) < 0)
    TRACE("Failed opening data buffer : %m\n");

  // test if stats type available 
  size_t i;
  struct stats_type *type;    
  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL) {
    type->st_enabled = 1;
    if (stats_type_init(type) < 0) {
      type->st_enabled = 0;
      continue;
    }    
    if (type->st_begin != NULL)
      (*type->st_begin)(type);
  }

  stats_wr_hdr(&sf);
  send_stats_buffer(&sf);
  stats_buffer_close(&sf);  

  // Cleanup
  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL)
    stats_type_destroy(type);    
}


/* Send data based on ev timer interval */
static void sample_timer_cb(struct ev_loop *loop, ev_timer *w, int revents) 
{
  pscanf(JOBID_FILE_PATH, "%79s", jobid);  

  struct stats_buffer sf;
  if (stats_buffer_open(&sf, server, port, queue) < 0)
    TRACE("Failed opening data buffer : %m\n");

  send_stats_buffer(&sf);
  stats_buffer_close(&sf);  
}

/* Collect and send data based on IO to JOBID file */
static void fd_cb(EV_P_ ev_io *w, int revents)
{
  //fprintf(log_stream, "reading jobid from fd\n");

  struct stats_buffer sf;
  if (stats_buffer_open(&sf, server, port, queue) < 0)
    TRACE("Failed opening data buffer : %m\n");

  char new_jobid[80] = "-";
  pscanf(JOBID_FILE_PATH, "%79s", new_jobid);  

  //printf("newjobid %s oldjobid %s\n", new_jobid, jobid);
  
  if (strcmp(jobid, new_jobid) != 0) {               
    if (strcmp(new_jobid, "-") != 0) {                
      strcpy(jobid, new_jobid);
      fprintf(log_stream, "Loading jobid %s from %s\n", jobid, JOBID_FILE_PATH);	
      stats_buffer_mark(&sf, "begin %s", jobid);
      sample_timer.repeat = freq; 
    }
    else {
      fprintf(log_stream, "Unloading jobid %s from %s\n", jobid, JOBID_FILE_PATH);	
      stats_buffer_mark(&sf, "end %s", jobid);
      sample_timer.repeat = 3600; 
    }
    ev_timer_again(EV_DEFAULT, &sample_timer);
  }
  
  // test if stats type available 
  size_t i;
  struct stats_type *type;    
  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL) {
    type->st_enabled = 1;
    if (stats_type_init(type) < 0) {
      type->st_enabled = 0;
      continue;
    }

    if (type->st_begin != NULL)
      (*type->st_begin)(type);
  }
  send_stats_buffer(&sf);    
  stats_buffer_close(&sf);

  strcpy(jobid, new_jobid);

  // Cleanup
  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL)
    stats_type_destroy(type);    
}

/* Signal Callbacks for SIGINT (terminate) and SIGHUP (reload conf file) */
static void signal_cb_int(EV_P_ ev_signal *sig, int revents)
{

  size_t i;
  struct stats_type *type;

  // Cleanup
  /*
  i = 0;
  while ((type = stats_type_for_each(&i)) != NULL)
    stats_type_destroy(type);    
  */
  fprintf(log_stream, "Stopping tacc_statsd\n");
  if (pid_fd != -1) {
    lockf(pid_fd, F_ULOCK, 0);
    close(pid_fd);
  }
  if (pid_file_name != NULL) {
    unlink(pid_file_name);
  }
  ev_break (EV_A_ EVBREAK_ALL);
}
static void signal_cb_hup(EV_P_ ev_signal *sig, int revents) 
{
  fprintf(log_stream, "Reloading tacc_statsd config file %s\n", conf_file_name);
  read_conf_file();    
  sample_timer.repeat = freq; 
  ev_timer_again(EV_DEFAULT, &sample_timer);
}


static void usage(void)
{
  fprintf(stderr,
          "Usage: %s [OPTION]... [TYPE]...\n"
          "Collect statistics.\n"
          "\n"
          "Mandatory arguments to long options are mandatory for short options too.\n"
          "  -h, --help         display this help and exit\n"
          "  -c [CONFIGFILE] or --configfile [CONFIGFILE] Configuration file to use.\n"
          "  -s [SERVER]     or --server     [SERVER]     Server to send data.\n"
          "  -q [QUEUE]      or --queue      [QUEUE]      Queue to route data to on RMQ server. \n"
          "  -p [PORT]       or --port       [PORT]       Port to use (5672 is the default).\n"
          "  -f [FREQUENCY]  or --frequency  [FREQUENCY]  Frequency to sample (600 seconds is the default).\n"
          ,
          program_invocation_short_name);
}

int main(int argc, char *argv[])
{
  int daemonmode = 0;
  char *log_file_name = NULL;

  app_name = argv[0];

  struct option opts[] = {
    { "help",      no_argument, 0, 'h' },
    { "daemon",    no_argument, 0, 'd' },
    { "server",    required_argument, 0, 's' },
    { "queue",     required_argument, 0, 'q' },
    { "port",      required_argument, 0, 'p' },
    { "conf_file", required_argument, 0, 'c'},
    { "frequency", required_argument, 0, 'f' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "hdc:s:q:f:p:", opts, 0)) != -1) {
    switch (c) {
    case 'd':
      daemonmode = 1;
      break;     
    case 's':
      server = strdup(optarg);
      break;
    case 'f':
      freq = atof(optarg);
      break;
    case 'c':    
      conf_file_name = strdup(optarg);
      break;
    case 'q':
      queue = strdup(optarg);
      break;
    case 'p':
      port = strdup(optarg);
      break;
    case 'h':
      usage();
      exit(0);
    case '?':
      fprintf(stderr, "Try `%s --help' for more information.\n", program_invocation_short_name);
      exit(1);
    }
  }

  log_stream = stderr;  

  /* Read configuration from config file */
  read_conf_file();

  if (daemonmode) {
    if (pid_file_name == NULL) 
      pid_file_name = strdup("/var/run/tacc_statsd.pid");
    daemonize();
  }

  fprintf(log_stream, "Started %s\n", app_name);

  /* Setup signal callbacks to stop tacc_statsd or reload conf file */
  signal(SIGPIPE, SIG_IGN);
  static struct ev_signal sigint;
  ev_signal_init(&sigint, signal_cb_int, SIGINT);
  ev_signal_start(EV_DEFAULT, &sigint);

  static struct ev_signal sighup;
  ev_signal_init(&sighup, signal_cb_hup, SIGHUP);
  ev_signal_start(EV_DEFAULT, &sighup);
  
  if (server == NULL) {
    fprintf(log_stream, "Must specify a server to send data to with -s [--server] argument or conf file.\n");
    exit(0);
  } else {    
    fprintf(log_stream, "tacc_statsd data to server %s on port %s.\n", server, port);
  }

  ev_stat fd_watcher;  

  /* Initialize timer routine to rotate file */
  ev_timer_init(&rotate_timer, rotate_timer_cb, 0.0, 86400);   
  ev_timer_start(EV_DEFAULT, &rotate_timer);
  fprintf(log_stream, "Setting tacc_statsd rotate log files every %ds\n", 86400);

  /* Initialize callback to respond to writes to job_fd */
  ev_stat_init(&fd_watcher, fd_cb, JOBID_FILE_PATH, EV_READ);
  ev_stat_start(EV_DEFAULT, &fd_watcher);    
  fprintf(log_stream, "Starting tacc_statsd watching fd %s\n", JOBID_FILE_PATH);
  
  /* Initialize timer routine to collect and send data */
  ev_timer_init(&sample_timer, sample_timer_cb, freq, freq);   
  ev_timer_start(EV_DEFAULT, &sample_timer);
  fprintf(log_stream, "Setting tacc_statsd sample frequency to %.1fs\n", freq);

  nr_cpus = sysconf(_SC_NPROCESSORS_ONLN);
  processor = signature(&n_pmcs);

  ev_run(EV_DEFAULT, 0);

  /* Write system log and close it. */
  fprintf(log_stream, "Stopped %s\n", app_name);

  /* Free up names of files */
  if (conf_file_name != NULL) free(conf_file_name);
  if (log_file_name != NULL) free(log_file_name);
  if (pid_file_name != NULL) free(pid_file_name);

  return EXIT_SUCCESS;
}
