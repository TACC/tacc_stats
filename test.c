#define _GNU_SOURCE
#include <stdio.h>
#include "stats.h"

int main(int argc, char *argv[])
{
  read_all_stats();
  print_all_stats(stdout, NULL);

  return 0;
}
