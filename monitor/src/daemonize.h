#ifndef _DAEMONIZE_H_
#define _DAEMONIZE_H_

#include <stdlib.h>

extern int pid_fd;
extern char *pid_file_name;
void daemonize();

#endif
