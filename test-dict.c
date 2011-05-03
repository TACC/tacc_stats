#define _GNU_SOURCE
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <mntent.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <malloc.h>
#include "dict.h"

#define TRACE ERROR

#define ERROR(fmt,arg...) \
  fprintf(stderr, "%s: "fmt, program_invocation_short_name, ##arg)

#define FATAL(fmt,arg...) do { \
    ERROR(fmt, ##arg);         \
    exit(1);                   \
  } while (0)

#define print_dict(d) do { \
  struct dict_entry *_de; \
  size_t _i = 0, _m; \
  while ((_de = dict_for_each_ref(&d, &_i)) != NULL) { \
    _m = _de->d_hash % d.d_table_len; \
    TRACE("%s: dict %s, i %zu, key `%s', hash %zu, hmod %zu %s\n", \
          __func__, #d, _i - 1, _de->d_key, _de->d_hash, _m, _m == _i - 1 ? "" : "*"); \
} \
} while (0)

void test1(void)
{
  DEFINE_DICT(d);
  print_dict(d);
  dict_destroy(&d);
}

void test2(void)
{
  DEFINE_DICT(d);
  dict_init(&d, 16);
  dict_set(&d, "foo");
  print_dict(d);
  dict_destroy(&d);
}

void test3(void)
{
  DEFINE_DICT(d);
  dict_init(&d, 16);
  size_t i;
  for (i = 0; i < 100; i++)
    dict_set(&d, "foo");
  print_dict(d);
  dict_destroy(&d);
}

void test4(void)
{
  DEFINE_DICT(d);
  dict_init(&d, 16);

  size_t i;
  for (i = 0; i < 100; i++) {
    char *key = NULL, *old;
    asprintf(&key, "foo%d", (int) i);
    old = dict_ref(&d, key);
    if (old != NULL)
      TRACE("dict_ref(&d, \"%s\") returned \"%s\"\n", key, old);
    if (dict_set(&d, key) < 0)
      ERROR("dict_set(&d, \"%s\") failed: %m\n", key);
  }
  print_dict(d);
  dict_destroy(&d);
}

void test5(void)
{
  DEFINE_DICT(d);
  dict_init(&d, 16);

  size_t i;
  char *key, *old, buf[80];

  for (i = 0; i < 100; i++) {
    key = NULL;
    asprintf(&key, "foo%d", (int) i);
    if (dict_set(&d, key) < 0)
      ERROR("dict_set(&d, \"%s\") failed: %m\n", key);
  }

  for (i = 0; i < 100; i += 2) {
    snprintf(buf, sizeof(buf), "foo%d", (int) i);
    old = dict_remv(&d, buf);
    if (old == NULL)
      ERROR("missing key `%s'\n", buf);
    free(old);
  }
  print_dict(d);

  while (1) {
    i = 0;
    key = dict_for_each(&d, &i);
    if (key == NULL)
      break;
    free(dict_remv(&d, key));
  }

  i = 0;
  key = dict_for_each(&d, &i);
  if (key != NULL)
    ERROR("dict should be empty but contains key `%s'\n", key);

  dict_destroy(&d);
}

int main(int argc, char *argv[])
{
  test1();
  test2();
  test3();
  test4();
  test5();

  return 0;
}
