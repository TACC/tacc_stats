#ifndef _DAEMONIZE_H_
#define _DAEMONIZE_H_

#include <stdlib.h>

int pid_fd;
char *pid_file_name;
void daemonize();

#endif
