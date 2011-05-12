#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <dirent.h>
#include <mntent.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include "stats.h"
#include "trace.h"
#include "dict.h"
#include "string1.h"

#define OBD_IOC_GETNAME 0xC0086683
#define LLITE_DIR_PATH "/proc/fs/lustre/llite"

/* Based on llite_opcode_table in lustre-1.8.5/lustre/llite/lproc_llite.c.

   In read_bytes, count is based on argument to read(), not return value.
   direct_{read,write} are not counted in {read,write}_bytes.
   direct_{read,write} are tallied in bytes not pages.
   brw_read is tallied in bytes not pages, and is only used in
   ll_prepare_write() when the write is not a complete page.
   brw_write is not used.
   lockless_{read,write}_bytes values seem to be same as direct_{read,write}.
   The writeback_* stats are unused.
   lockless_truncates are a subset of truncates.

   If you find out what 'regs' are then please let me know.
*/

#define KEYS \
  X(read_bytes, "E,U=B", ""), \
  X(write_bytes, "E,U=B", ""), \
  X(direct_read, "E,U=B", ""), \
  X(direct_write, "E,U=B", ""), \
  X(dirty_pages_hits, "E", ""), \
  X(dirty_pages_misses, "E", ""), \
  X(ioctl, "E", ""), \
  X(open, "E", ""), \
  X(close, "E", ""), \
  X(mmap, "E", ""), \
  X(seek, "E", ""), \
  X(fsync, "E", ""), \
  X(setattr, "E", ""), \
  X(truncate, "E", ""), \
  X(flock, "E", ""), \
  X(getattr, "E", ""), \
  X(statfs, "E", ""), \
  X(alloc_inode, "E", ""), \
  X(setxattr, "E", ""), \
  X(getxattr, "E", ""), \
  X(listxattr, "E", ""), \
  X(removexattr, "E", ""), \
  X(inode_permission, "E", "")

static int sb_dict_init(struct dict *sb_dict)
{
  int rc = -1;
  const char *me_path = "/proc/mounts";
  FILE *me_file = NULL;

  if (dict_init(sb_dict, 8) < 0) {
    ERROR("cannot create sb_dict: %m\n");
    goto out;
  }

  me_file = setmntent(me_path, "r");
  if (me_file == NULL) {
    ERROR("cannot open `%s': %m\n", me_path);
    goto out;
  }

  struct mntent me;
  char me_buf[4096];
  while (getmntent_r(me_file, &me, me_buf, sizeof(me_buf)) != NULL) {
    int me_dir_fd = -1;
    char me_lov_uuid[40] = "";

    if (strcmp(me.mnt_type, "lustre") != 0)
      goto next;

    me_dir_fd = open(me.mnt_dir, O_RDONLY);
    if (me_dir_fd < 0) {
      ERROR("cannot open `%s': %m\n", me.mnt_dir);
      goto next;
    }

    if (ioctl(me_dir_fd, OBD_IOC_GETNAME, me_lov_uuid) < 0) {
      ERROR("cannot get lov uuid for `%s': %m\n", me.mnt_dir);
      goto next;
    }

    /* mnt_lov_uuid is of the form `work-clilov-ffff8102658ec800'. */
    if (strlen(me_lov_uuid) < 24) {
      ERROR("unrecognized lov uuid `%s'\n", me_lov_uuid);
      goto next;
    }

    /* Get superblock address (the `ffff8102658ec800' part). */
    const char *sb = me_lov_uuid + strlen(me_lov_uuid) - 16;
    hash_t sb_hash = dict_strhash(sb);
    struct dict_entry *sb_ent = dict_entry_ref(sb_dict, sb_hash, sb);
    if (sb_ent->d_key != NULL) {
      TRACE("multiple filesystems with sb `%s'\n", sb);
      goto next;
    }

    char *sb_key = malloc(strlen(sb) + 1 + strlen(me.mnt_dir) + 1);
    if (sb_key == NULL) {
      ERROR("cannot allocate sb_key: %m\n");
      goto next;
    }

    strcpy(sb_key, sb);
    strcpy(sb_key + strlen(sb) + 1, me.mnt_dir);

    if (dict_entry_set(sb_dict, sb_ent, sb_hash, sb_key) < 0) {
      ERROR("cannot set sb_dict entry: %m\n");
      free(sb_key);
      goto next;
    }

    TRACE("fsname `%s', dir `%s', type `%s', lov_uuid `%s', sb `%s'\n",
          me.mnt_fsname, me.mnt_dir, me.mnt_type, me_lov_uuid, sb);

  next:
    if (me_dir_fd >= 0)
      close(me_dir_fd);
  }
  rc = 0;
 out:
  if (me_file != NULL)
    endmntent(me_file);
  return rc;
}

static void collect_llite_fs(struct stats *stats, const char *d_name)
{
  char *path = NULL;
  FILE *file = NULL;
  char *line_buf = NULL;
  size_t line_buf_size = 0;

  if (asprintf(&path, "%s/%s/stats", LLITE_DIR_PATH, d_name) < 0) {
    ERROR("cannot create path: %m\n");
    goto out;
  }

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  // $ cat /proc/fs/lustre/llite/scratch-ffff81019a4eb000/stats
  // snapshot_time             1301585789.189183 secs.usecs
  // dirty_pages_hits          276 samples [regs]
  // dirty_pages_misses        57841029 samples [regs]
  // read_bytes                449131 samples [bytes] 1 23553884 101262334767
  // write_bytes               201770 samples [bytes] 1 20971520 236938468092
  // brw_read                  13 samples [pages] 4096 4096 53248
  // ioctl                     8050 samples [regs]

  /* Skip snapshot. */
  getline(&line_buf, &line_buf_size, file);

  while (getline(&line_buf, &line_buf_size, file) >= 0) {
    char *line = line_buf;
    char *key = wsep(&line);
    if (key == NULL || line == NULL)
      continue;

    unsigned long long count = 0, sum = 0;
    int n = sscanf(line, "%llu samples %*s %*u %*u %llu", &count, &sum);
    if (n == 1)
      stats_set(stats, key, count);
    else if (n == 2)
      stats_set(stats, key, sum);
  }

 out:
  free(line_buf);
  if (file != NULL)
    fclose(file);
  free(path);
}

static void collect_llite(struct stats_type *type)
{
  const char *llite_dir_path = LLITE_DIR_PATH;
  DIR *llite_dir = NULL;
  DEFINE_DICT(sb_dict);

  if (sb_dict_init(&sb_dict) < 0) {
    ERROR("cannot create sb_dict: %m\n");
    goto out;
  }

  TRACE("found %zu lustre filesystems\n", sb_dict.d_count);
  if (sb_dict.d_count == 0)
    goto out;

#ifdef DEBUG
  do {
    size_t i = 0;
    char *sb;
    while ((sb = dict_for_each(&sb_dict, &i)) != NULL)
      TRACE("sb `%s', dir `%s'\n", sb, sb + strlen(sb) + 1);
  } while (0);
#endif

  llite_dir = opendir(llite_dir_path);
  if (llite_dir == NULL) {
    ERROR("cannot open `%s': %m\n", llite_dir_path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(llite_dir)) != NULL) {
    struct stats *stats = NULL;
    char *name = ent->d_name, *sb, *sb_ref, *mnt;

    if (*name == '.' || strlen(name) < 16)
      continue;

    sb = name + strlen(name) - 16;
    sb_ref = dict_ref(&sb_dict, sb);
    if (sb_ref == NULL) {
      ERROR("no superblock found for llite entry `%s'\n", name);
      continue;
    }

    mnt = sb_ref + strlen(sb_ref) + 1;
    TRACE("ent `%s', sb_ref `%s', mnt `%s'\n", name, sb_ref, mnt);

    stats = get_current_stats(type, mnt);
    if (stats == NULL)
      continue;

    collect_llite_fs(stats, name);
  }

 out:
  dict_destroy(&sb_dict, &free);

  if (llite_dir != NULL)
    closedir(llite_dir);
}

struct stats_type llite_stats_type = {
  .st_name = "llite",
  .st_collect = &collect_llite,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
