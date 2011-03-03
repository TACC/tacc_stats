#ifndef _COLLECT_H_
#define _COLLECT_H_

int collect_single(unsigned long long *dest, const char *path);

int collect_key_value_file(struct stats *stats, const char *path);

int collect_key_value_dir(struct stats *stats, const char *path);

#endif
