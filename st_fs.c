#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "stats.h"
#include "collect.h"
#include "trace.h"

static void collect_fs(struct stats_type *type)
{
  struct stats *stats = NULL;

  stats = get_current_stats(type, NULL);
  if (stats == NULL)
    return;

/* $ cat /proc/sys/fs/dentry-state
   850986 838906 45 0 0 0

   This file contains six numbers, nr_dentry, nr_unused, age_limit
   (age in seconds), want_pages (pages requested by system) and two
   dummy values.  nr_dentry seems to be 0 all the time.  nr_unused
   seems to be the number of unused dentries.  age_limit is the age in
   seconds after which dcache entries can be reclaimed when memory is
   short and want_pages is non-zero when the kernel has called
   shrink_dcache_pages() and the dcache t pruned yet. */

  unsigned long long nr_dentry = 0, nr_unused = 0;
  if (collect_list("/proc/sys/fs/dentry-state", &nr_dentry, &nr_unused, NULL) == 2)
    stats_set(stats, "nr_dentry_used", nr_dentry - nr_unused);

/* $ cat /proc/sys/fs/file-nr
   6080 0 1174404

   Historically, the three values in file-nr denoted the number of
   allocated file handles, the number of allocated but unused file
   handles, and the maximum number of file handles. Linux 2.6 always
   reports 0 as the number of free file handles -- this is not an
   error, it just means that the number of allocated file handles
   exactly matches the number of used file handles. */

  unsigned long long nr_files = 0;
  collect_single("/proc/sys/fs/file-nr", &nr_files);
  stats_set(stats, "nr_files_used", nr_files);

/* $ cat /proc/sys/fs/inode-state
   168192 59759 0 0 0 0 0

   This file contains seven numbers: nr_inodes, nr_free_inodes,
   preshrink and four dummy values.  nr_inodes is the number of inodes
   the system has allocated.  This can be slightly more than inode-max
   because Linux allocates them one page full at a time.
   nr_free_inodes represents the number of free inodes.  preshrink is
   non-zero when the nr_inodes > inode-max and the system needs to
   prune the inode list instead of allocating more. */

  unsigned long long nr_inodes = 0, nr_free_inodes = 0;
  if (collect_list("/proc/sys/fs/inode-state", &nr_inodes, &nr_free_inodes, NULL) == 2)
    stats_set(stats, "nr_inodes_used", nr_inodes - nr_free_inodes);
}

struct stats_type ST_FS_TYPE = {
  .st_name = "fs",
  .st_collect = &collect_fs,
  .st_schema = (char *[]) { "nr_dentry_used", "nr_files_used", "nr_inodes_used", NULL, },
};
