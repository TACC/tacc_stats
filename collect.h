#ifndef _COLLECT_H_
#define _COLLECT_H_

struct stats;

int collect_single(const char *path, unsigned long long *dest);

int collect_list(const char *path, ...);

int collect_key_list(struct stats *stats, const char *path, ...);

int collect_key_value_file(struct stats *stats, const char *path);

int collect_key_value_dir(struct stats *stats, const char *path);

#endif
