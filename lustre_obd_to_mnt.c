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
#include "lustre_obd_to_mnt.h"

#define OBD_IOC_GETNAME 0xC0086683

struct dict sb_dict;

__attribute__((constructor))
static void sb_dict_init(void)
{
  const char *me_path = "/proc/mounts";
  FILE *me_file = NULL;

  if (dict_init(&sb_dict, 8) < 0) {
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
    int dir_fd = -1;
    char lov_name[128] = "";
    char *sb_mnt = NULL;

    if (strcmp(me.mnt_type, "lustre") != 0)
      goto next;

    dir_fd = open(me.mnt_dir, O_RDONLY);
    if (dir_fd < 0) {
      ERROR("cannot open `%s': %m\n", me.mnt_dir);
      goto next;
    }

    if (ioctl(dir_fd, OBD_IOC_GETNAME, lov_name) < 0) {
      ERROR("cannot get lov name for `%s': %m\n", me.mnt_dir);
      goto next;
    }

    /* lov_name is of the form `work-clilov-ffff8102658ec800'. */
    if (strlen(lov_name) < 16) {
      ERROR("invalid lov name `%s'\n", lov_name);
      goto next;
    }

    /* Get superblock address (the `ffff8102658ec800' part). */
    const char *sb = lov_name + strlen(lov_name) - 16;
    hash_t hash = dict_strhash(sb);
    struct dict_entry *de = dict_entry_ref(&sb_dict, hash, sb);
    if (de->d_key != NULL) {
      TRACE("multiple filesystems with super block `%s'\n", sb);
      goto next;
    }

    sb_mnt = malloc(16 + 1 + strlen(me.mnt_dir) + 1);
    if (sb_mnt == NULL) {
      ERROR("cannot allocate sb_mnt: %m\n");
      goto next;
    }

    strcpy(sb_mnt, sb);
    strcpy(sb_mnt + 16 + 1, me.mnt_dir);

    if (dict_entry_set(&sb_dict, de, hash, sb_mnt) < 0) {
      ERROR("cannot set sb_dict entry: %m\n");
      free(sb_mnt);
      goto next;
    }

    TRACE("fsname `%s', dir `%s', type `%s', lov_uuid `%s', sb `%s'\n",
          me.mnt_fsname, me.mnt_dir, me.mnt_type, lov_name, sb);

  next:
    if (dir_fd >= 0)
      close(dir_fd);
  }

 out:
  if (me_file != NULL)
    endmntent(me_file);

  TRACE("found %zu lustre filesystems\n", sb_dict.d_count);

#ifdef DEBUG
  do {
    size_t i = 0;
    char *sb_mnt;
    while ((sb_mnt = dict_for_each(&sb_dict, &i)) != NULL)
      TRACE("sb `%s', mnt `%s'\n", sb_mnt, sb_mnt + 16 + 1);
  } while (0);
#endif
}

char *lustre_obd_to_mnt(const char *name)
{
  char *sb_mnt;

  /* name should be of the form `work-clilov-ffff8102658ec800'. */

  if (strlen(name) < 16) {
    ERROR("invalid obd name `%s'\n", name);
    return NULL;
  }

  sb_mnt = dict_ref(&sb_dict, name + strlen(name) - 16);
  if (sb_mnt == NULL) {
    ERROR("no super block found for obd `%s'\n", name);
    return NULL;
  }

  return sb_mnt + 16 + 1;
}

/* XXX dict_destroy(&sb_dict, &free); */
