#define _GNU_SOURCE
#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include "dict.h"

int main(int argc, char *argv[])
{
  struct dict dict;
  dict_init(&dict, 0);

  while (1) {
    char *line = NULL;
    size_t line_size = 0;

    if (getline(&line, &line_size, stdin) <= 0)
      break;

    char *s = strchr(line, '\n');
    if (s != NULL)
      *s = 0;

    dict_search(&dict, line);
  }

  size_t i = 0;
  const char *key;

  while ((key = dict_for_each(&dict, &i)) != NULL)
    printf("%s\n", key);

  return 0;
}
