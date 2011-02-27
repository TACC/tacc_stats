#ifndef _STATS_H_
#define _STATS_H_

enum {
#define X(t) t ,
#include "stats.x"
#undef X
};

extern char *st_name[];

struct stats;
struct stats *get_current_stats(int type, const char *id);
void stats_set(struct stats *s, char *key, unsigned long long val);
void stats_set_unit(struct stats *s, char *key, unsigned long long val, const char *unit);

void read_proc_stat(void);
void read_loadavg();
void read_meminfo(void);
void read_vmstat(void);
void read_jobid();
void read_ib_stats();

int read_single(const char *path, unsigned long long *dest);
int read_key_value(const char *path, struct stats *stats);

#endif
