#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <sys/wait.h>
#include "trace.h"

int helper(const char *path, char *const argv[], char *const envp[])
{
  pid_t pid = fork();
  if (pid == -1) {
    ERROR("cannot execute `%s': %m\n", path);
    return -1;
  }

  if (pid == 0) {
    if (setuid(0) < 0)
      FATAL("cannot set user id to 0: %m\n");
    execve(path, argv, envp);
    _exit(127);
  }

  int stat;
  while (waitpid(pid, &stat, 0) == -1) {
    if (errno != EINTR) {
      ERROR("cannot obtain termination status of `%s': %m\n", path);
      return -1;
    }
  }

  if (WIFSIGNALED(stat)) {
    int term_sig = WTERMSIG(stat);
    TRACE("`%s' terminated by signal %d\n", path, term_sig);
    return -1;
  }

  int exit_stat = WEXITSTATUS(stat);
  TRACE("`%s' exited with status %d\n", path, exit_stat);
  return exit_stat;
}
