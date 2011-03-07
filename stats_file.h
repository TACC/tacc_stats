#ifndef _STATS_FILE_H_
#define _STATS_FILE_H_

int stats_file_wr_hdr(FILE *file, const char *path);
int stats_file_rd_hdr(FILE *file, const char *path);
int stats_file_wr_rec(FILE *file, const char *path, const char *jobid);

#endif
