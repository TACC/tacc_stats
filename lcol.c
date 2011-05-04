#define _GNU_SOURCE
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
#include <mntent.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <malloc.h>
#include <dirent.h>
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

int sb_dict_init(struct dict *sb_dict)
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
    char me_lov_uuid[40];

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

int main(int argc, char *argv[])
{
  DEFINE_DICT(sb_dict);
  const char *osc_path = "/proc/fs/lustre/osc";
  DIR *osc_dir = NULL;

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

  osc_dir = opendir(osc_path);
  if (osc_dir == NULL) {
    ERROR("cannot open `%s': %m\n", osc_path);
    goto out;
  }

  struct dirent *osc;
  while ((osc = readdir(osc_dir)) != NULL) {
    if (*osc->d_name == '.' || strcmp(osc->d_name, "num_refs") == 0)
      continue;

    if (strlen(osc->d_name) < 16) {
      ERROR("unrecognized osc name `%s'\n", osc->d_name);
      continue;
    }

    char *osc_sb = osc->d_name + strlen(osc->d_name) - 16;
    char *sb_ref = dict_ref(&sb_dict, osc_sb);
    if (sb_ref == NULL) {
      ERROR("no superblock found for osc `%s'\n", osc->d_name);
      continue;
    }
    char *fs_mnt = sb_ref + strlen(sb_ref) + 1;
    TRACE("osc `%s', sb_ref `%s', fs_mnt `%s'\n", osc->d_name, sb_ref, fs_mnt);
  }

 out:
  dict_destroy(&sb_dict, &free);

  if (osc_dir != NULL)
    closedir(osc_dir);

  return 0;
}
