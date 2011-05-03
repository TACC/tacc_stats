#define _GNU_SOURCE
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
#include <mntent.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <malloc.h>
#include <sys/ioctl.h>
#include "dict.h"

#define OBD_IOC_GETNAME 0xC0086683

#define TRACE ERROR

#define ERROR(fmt,arg...) \
  fprintf(stderr, "%s: "fmt, program_invocation_short_name, ##arg)

#define FATAL(fmt,arg...) do { \
    ERROR(fmt, ##arg);         \
    exit(1);                   \
  } while (0)

int main(int argc, char *argv[])
{
  const char *mnt_path = "/proc/mounts";
  FILE *mnt_file = NULL;
  struct mntent mnt;
  char buf[4096];
  DEFINE_DICT(sb_dict);

  if (dict_init(&sb_dict, 8) < 0) {
    ERROR("cannot create sb_dict: %m\n");
    goto out;
  }

  mnt_file = setmntent(mnt_path, "r");
  if (mnt_file == NULL) {
    ERROR("cannot open `%s': %m\n", mnt_path);
    goto out;
  }

  while (getmntent_r(mnt_file, &mnt, buf, sizeof(buf)) != NULL) {
    int mnt_dir_fd = -1;
    char mnt_lov_uuid[40];

    if (strcmp(mnt.mnt_type, "lustre") != 0)
      goto next;

    mnt_dir_fd = open(mnt.mnt_dir, O_RDONLY);
    if (mnt_dir_fd < 0) {
      ERROR("cannot open `%s': %m\n", mnt.mnt_dir);
      goto next;
    }

    if (ioctl(mnt_dir_fd, OBD_IOC_GETNAME, mnt_lov_uuid) < 0) {
      ERROR("cannot get lov uuid for `%s': %m\n", mnt.mnt_dir);
      goto next;
    }

    /* mnt_lov_uuid is of the form `work-clilov-ffff8102658ec800'. */
    if (strlen(mnt_lov_uuid) < 24) {
      ERROR("unrecognized lov uuid `%s'\n", mnt_lov_uuid);
      goto next;
    }

    /* Get superblock address (the `ffff8102658ec800' part). */
    const char *sb = mnt_lov_uuid + strlen(mnt_lov_uuid) - 16;
    hash_t sb_hash = dict_strhash(sb);
    struct dict_entry *sb_ent = dict_entry_ref(&sb_dict, sb_hash, sb);
    if (sb_ent->d_key != NULL) {
      /* Maybe bad. */
      goto next;
    }

    char *sb_key = malloc(strlen(sb) + 1 + strlen(mnt.mnt_dir) + 1);
    if (sb_key == NULL) {
      ERROR("cannot allocate sb_key: %m\n");
      goto next;
    }

    strcpy(sb_key, sb);
    strcpy(sb_key + strlen(sb) + 1, mnt.mnt_dir);

    if (dict_entry_set(&sb_dict, sb_ent, sb_hash, sb_key) < 0) {
      ERROR("cannot set sb_dict entry: %m\n");
      free(sb_key);
      goto next;
    }

    TRACE("fsname `%s', dir `%s', type `%s', lov_uuid `%s', sb `%s'\n",
          mnt.mnt_fsname, mnt.mnt_dir, mnt.mnt_type, mnt_lov_uuid, sb);

  next:
    if (mnt_dir_fd >= 0)
      close(mnt_dir_fd);
  }

  TRACE("d_count %zu\n", sb_dict.d_count);

  size_t i = 0;
  char *sb;
  while ((sb = dict_for_each(&sb_dict, &i)) != NULL) {
    ERROR("sb `%s', dir `%s'\n", sb, sb + strlen(sb) + 1);
    free(sb);
  }

 out:
  dict_destroy(&sb_dict);

  if (mnt_file != NULL)
    endmntent(mnt_file);

  return 0;
}
