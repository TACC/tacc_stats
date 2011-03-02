#define _GNU_SOURCE
#include <stdio.h>
#include "stats.h"

int main(int argc, char *argv[])
{
  collect_all();
  print_all_stats(stdout, NULL);

  return 0;
}
