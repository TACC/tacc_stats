#ifndef _STATS_FILE_H_
#define _STATS_FILE_H_
#include <stdio.h>

struct stats_file {
  char *sf_path;
  FILE *sf_file;
};

int stats_file_rd_hdr(struct stats_file *sf);
int stats_file_wr_hdr(struct stats_file *sf);
int stats_file_wr_rec(struct stats_file *sf);
int stats_file_wr_mark(struct stats_file *sf, const char *str);

#endif
