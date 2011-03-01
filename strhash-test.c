#include <stdio.h>

unsigned long strhash(const char *s);

int main(int argc, char *argv[])
{
  printf("%016lx\n", strhash(argv[1]));

  return 0;
}
