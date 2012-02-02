#ifndef _COLLECT_H_
#define _COLLECT_H_

#if GCC_VERSION >= 3005
#define __ATTRIBUTE__SENTINEL __attribute__((sentinel))
#else
#define __ATTRIBUTE__SENTINEL
#endif

struct stats;

int collect_single(const char *path, unsigned long long *dest);
int collect_list(const char *path, ...) __ATTRIBUTE__SENTINEL;
int collect_key_list(struct stats *stats, const char *path, ...) __ATTRIBUTE__SENTINEL;
int collect_key_value_file(struct stats *stats, const char *path);
int collect_key_value_dir(struct stats *stats, const char *path);

#endif
