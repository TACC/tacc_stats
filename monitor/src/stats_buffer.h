#ifndef _STATS_BUFFER_H_
#define _STATS_BUFFER_H_
#include <stdio.h>

struct stats_buffer {
  char *sf_mark;
  char *sf_data;
  char *sf_host;
  char *sf_queue;
  char *sf_port;
  unsigned int sf_empty:1;
};

#define MAX_SF_Q 1000

struct sf_requeue {
  struct sf_requeue *q_forward;
  struct sf_requeue *q_back;
  struct stats_buffer *q_sf;
};

int stats_buffer_open(struct stats_buffer *sf, const char *host, const char *port, const char *queue);
int stats_buffer_mark(struct stats_buffer *sf, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
int stats_buffer_write(struct stats_buffer *sf);
int stats_wr_hdr(struct stats_buffer *sf);

#endif
