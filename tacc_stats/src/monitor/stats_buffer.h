#ifndef _STATS_BUFFER_H_
#define _STATS_BUFFER_H_
#include <stdio.h>

struct stats_buffer {
  char *sf_path;
  char *sf_mark;
  char *sf_data;
  char *sf_host;
  char *sf_port;
  unsigned int sf_empty:1;
};

int stats_buffer_open(struct stats_buffer *sf);
int stats_buffer_mark(struct stats_buffer *sf, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
int stats_buffer_write(struct stats_buffer *sf);
int stats_wr_hdr(struct stats_buffer *sf);

#endif
