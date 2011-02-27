#include "stats.h"

char *st_name[] = {
#define X(t) [t] = #t ,
#include "stats.x"
#undef X
};
