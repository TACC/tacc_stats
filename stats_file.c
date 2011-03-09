#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <limits.h>
#include <stdarg.h>
#include <sys/utsname.h>
#include "stats.h"
#include "stats_file.h"
#include "trace.h"
#include "split.h"

#define SPACE_CHARS " \t\n\v\f\r"

int stats_file_rd_hdr(FILE *file, const char *path)
{
  int rc = 0;
  char *buf = NULL, *line;
  size_t size = 0;

  if (getline(&buf, &size, file) <= 0) {
    ERROR("file `%s' is not in %s format\n", path, TACC_STATS_PROGRAM);
    goto err;
  }

  line = buf;
  char *prog = strsep(&line, SPACE_CHARS);
  if (prog == NULL || strcmp(prog, TACC_STATS_PROGRAM) != 0) {
    ERROR("file `%s' is not in %s format\n", path, TACC_STATS_PROGRAM);
    goto err;
  }

  char *vers = strsep(&line, SPACE_CHARS);
  if (vers == NULL || strverscmp(vers, TACC_STATS_VERSION) > 0) {
    ERROR("file `%s' is has unsupported version `%s'\n", path, vers != NULL ? vers : "NULL");
    goto err;
  }

  TRACE("prog %s, vers %s\n", prog, vers);

  /* TODO Jobid in header. */
  /* Check for change of job. */

  int nr = 1;
  while (getline(&buf, &size, file) > 0) {
    nr++;
    line = buf;

    int c = *(line++);
    if (c == '\n')
      break; /* End of header. */

    if (c == '#')
      continue; /* Comment. */

    if (c == '$') {
      /* TODO if (tacc_stats_config(line) < 0)
         goto err; */
      continue;
    }

    /* Otherwise line is a directive to be processed by a type. */
    char *name = strsep(&line, SPACE_CHARS);
    if (*name == 0 || line == NULL) {
      line = "";
      ERROR("%s:%d: bad directive `%c%s %s'\n", path, nr, c, name, line);
      goto err;
    }

    struct stats_type *type = name_to_type(name);
    if (type == NULL) {
      ERROR("%s:%d: unknown type `%s'\n", path, nr, name);
      goto err;
    }

    TRACE("%s:%d: c %c, name %s, rest %s\n", path, nr, c, name, line);
    switch (c) {
    case '.':
      if (type->st_rd_config == NULL) {
        ERROR("type `%s' has no config method\n", type->st_name); /* XXX */
        goto err;
      }
      if ((*type->st_rd_config)(type, line) < 0)
        goto err;
      break;
    case '!':
      type->st_schema = split(line);
      if (type->st_schema == NULL) {
        ERROR("cannot parse schema: %m\n");
        goto err;
      }
      type->st_enabled = 1;
      break;
    case '@': /* TODO */
      break;
    default:
      ERROR("%s:%d: bad directive `%c%s %s'\n", path, nr, c, name, line);
      goto err;
    }
  }

  if (ferror(file)) {
    ERROR("error reading from `%s': %m\n", path);
  err:
    rc = -1;
    if (errno == 0)
      errno = EINVAL;
  }

  free(buf);

  return rc;
}

int stats_file_wr_hdr(FILE *file, const char *path)
{
  struct utsname uts_buf;
  uname(&uts_buf);

  fprintf(file, "%s %s\n", TACC_STATS_PROGRAM, TACC_STATS_VERSION);
  fprintf(file, "#hostname %s\n", uts_buf.nodename);
  fprintf(file, "#uname %s %s %s %s\n", uts_buf.sysname, uts_buf.machine,
          uts_buf.release, uts_buf.version);

  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (!type->st_enabled)
      continue;

    /* Write schema. */
    fprintf(file, "!%s", type->st_name);

    char **key;
    for (key = type->st_schema; *key != NULL; key++)
      fprintf(file, " %s", *key);

    fprintf(file, "\n");
  }

  return 0;
}

void stats_type_wr_stats(struct stats_type *type, FILE *file)
{
  size_t i = 0;
  struct dict_entry *ent;
  while ((ent = dict_for_each(&type->st_current_dict, &i)) != NULL) {
    struct stats *stats = (struct stats *) ent->d_key - 1;

    fprintf(file, "%s %s", type->st_name, stats->s_dev);

    char **key;
    for (key = type->st_schema; *key != NULL; key++)
      fprintf(file, " %llu", stats_get(stats, *key));

    fprintf(file, "\n");
  }
}

int stats_file_wr_rec(FILE *file, const char *path)
{
  fprintf(file, "\n%ld\n", (long) current_time);

  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL)
    if (type->st_enabled && type->st_selected)
      stats_type_wr_stats(type, file);

  return 0;
}

int stats_file_printf(FILE *file, const char *path, const char *fmt, ...)
{
  int rc;
  va_list args;

  va_start(args, fmt);
  rc = vfprintf(file, fmt, args);
  va_end(args);

  return rc;
}
