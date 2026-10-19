/* Regression: unresolved NSS (NULL pw_name) must not denylist non-root pids. */
#include <assert.h>
#include <stdio.h>

#include "proc_filter.h"

static void test_denylist_null_keeps(void)
{
  assert(proc_filter_is_denylisted_name(NULL) == 0);
}

static void test_denylist_system_accounts(void)
{
  assert(proc_filter_is_denylisted_name("postfix") == 1);
  assert(proc_filter_is_denylisted_name("rpc") == 1);
  assert(proc_filter_is_denylisted_name("rpcuser") == 1);
  assert(proc_filter_is_denylisted_name("dbus") == 1);
  assert(proc_filter_is_denylisted_name("daemon") == 1);
  assert(proc_filter_is_denylisted_name("ntp") == 1);
  assert(proc_filter_is_denylisted_name("sharrell") == 0);
  assert(proc_filter_is_denylisted_name("root") == 0);
}

int main(void)
{
  test_denylist_null_keeps();
  test_denylist_system_accounts();
  printf("test_proc_filter: ok\n");
  return 0;
}
