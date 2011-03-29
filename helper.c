#include <signal.h>
#include <unistd.h>
#include <sys/wait.h>
#include "trace.h"

extern const char *helper_path;

int helper(const char *arg)
{
  pid_t pid = fork();
  if (pid == -1) {
    ERROR("cannot execute `%s %s': %m\n", helper_path, arg);
    return -1;
  }

  if (pid == 0) {
    char *const env[] = { NULL, };
    execle(helper_path, arg, NULL, env);
    _exit(127);
  }

  int stat;
  while (waitpid(pid, &stat, 0) == -1) {
    if (errno != EINTR) {
      ERROR("cannot obtain termination status of `%s %s': %m\n", helper_path, arg);
      return -1;
    }
  }

  if (WIFSIGNALED(stat)) {
    int term_sig = WTERMSIG(stat);
    TRACE("`%s %s' terminated by signal %d\n", helper_path, arg, term_sig);
    return -1;
  }

  int exit_stat = WEXITSTATUS(stat);
  TRACE("`%s %s' exited with status %d\n", helper_path, arg, exit_stat);
  return exit_stat;
}
