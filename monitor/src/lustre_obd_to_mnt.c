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

/* 
This function grabs the super block address from 
each Lustre OBD names and allows it to be used a dictionary ref.
The key will be the lov name without the super block address.  
*/

struct dict sb_dict;

__attribute__((constructor))
static void sb_dict_init(void)
{
  char path[80];
  FILE *file= NULL;
  char file_buf[4096];
  char *line = NULL;
  size_t line_size = 0;

  if (dict_init(&sb_dict, 8) < 0) {
    ERROR("cannot create sb_dict: %m\n");
    goto out;
  }

  char lov_name[128] = "";
  char *sb_mnt = NULL;
  
  snprintf(path, sizeof(path), "/proc/fs/lustre/devices");
  file = fopen(path,"r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }
  setvbuf(file, file_buf, _IOFBF, sizeof(file_buf));
    
  /* Get lov name and use super block address as dict hash */
  while (getline(&line, &line_size, file) >= 0) {
    int num;
    char status[24];
    char type[24];
    
    sscanf(line,"%d %s %s %s",&num,status,type,lov_name);
    
    if (strcmp(type,"lov") != 0)
      continue;
    
    TRACE("num %d status %s type %s name %s\n",num,status,type,lov_name);
    
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
    
    /* Get name of lov w/ superblock address stripped */
    char *p;
    p = lov_name + strlen(lov_name) - 16 - 1;
    *p = '\0';

    sb_mnt = malloc(16 + 1 + strlen(lov_name) + 1);
    if (sb_mnt == NULL) {
      ERROR("cannot allocate sb_mnt: %m\n");
      goto next;
    }
    
    strcpy(sb_mnt, sb);
    strcpy(sb_mnt + 16 + 1, lov_name);
    
    if (dict_entry_set(&sb_dict, de, hash, sb_mnt) < 0) {
      ERROR("cannot set sb_dict entry: %m\n");
      free(sb_mnt);
      goto next;
    }

  next:
    continue;
  }

 out:

  free(line);
  if(file != NULL)
    fclose(file);
  
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
    ERROR("no super block found for obd `%s'. build a new super block dict\n", name);
    sb_dict_init();
    sb_mnt = dict_ref(&sb_dict, name + strlen(name) - 16);
  }

  return sb_mnt + 16 + 1;
}

/* XXX dict_destroy(&sb_dict, &free); */
