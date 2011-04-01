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
#include "schema.h"
#include "trace.h"

#define SPACE_CHARS " \t\n\v\f\r"

int stats_file_rd_hdr(FILE *file, const char *path)
{
  int rc = 0;
  char *buf = NULL, *line;
  size_t size = 0;

  if (getline(&buf, &size, file) <= 0) {
    if (feof(file))
      ERROR("empty stats file `%s'\n", path);
    goto err;
  }

  line = buf;
  if (*(line++) != '#') {
    ERROR("file `%s' is not in %s format\n", path, TACC_STATS_PROGRAM);
    goto err;
  }

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
  /* TODO Ignore whitespace. */

  int nr = 1;
  while (getline(&buf, &size, file) > 0) {
    nr++;
    line = buf;

    int c = *(line++);
    if (c == '\n')
      break; /* End of header. */

    if (c == '#')
      continue; /* Comment. */

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
    case '!':
      if (schema_init(&type->st_schema, line) < 0) {
        ERROR("cannot parse schema: %m\n");
        goto err;
      }
      type->st_enabled = 1;
      break;
    case '@': /* TODO Handle device list. */
      break;
    case '$': /* TODO */
      break;
    case '%': /* TODO */
      break;
    default:
      ERROR("%s:%d: bad directive `%c%s %s'\n", path, nr, c, name, line);
      goto err;
    }
  }

  if (ferror(file)) {
  err:
    rc = -1;
    if (errno == 0)
      errno = EINVAL;
  }

  if (ferror(file))
    ERROR("error reading from `%s': %m\n", path);

  free(buf);

  return rc;
}

int stats_file_wr_hdr(FILE *file, const char *path)
{
  struct utsname uts_buf;
  uname(&uts_buf);

  fprintf(file, "#%s %s\n", TACC_STATS_PROGRAM, TACC_STATS_VERSION);
  /* Make these global properties. */
  fprintf(file, "#hostname %s\n", uts_buf.nodename);
  fprintf(file, "#uname %s %s %s %s\n", uts_buf.sysname, uts_buf.machine,
          uts_buf.release, uts_buf.version);
  /* TODO btime. */

  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (!type->st_enabled)
      continue;

    TRACE("type %s, schema_len %zu\n", type->st_name, type->st_schema.sc_len);

    /* Write schema. */
    fprintf(file, "!%s", type->st_name);

    /* MOVEME */
    size_t j;
    for (j = 0; j < type->st_schema.sc_len; j++) {
      struct schema_entry *se = type->st_schema.sc_ent[j];
      fprintf(file, " %s%s%s", se->se_key,
              se->se_type == SE_EVENT ? ",E" : "",
              se->se_type == SE_BITS ? ",B" : "");
      if (se->se_width != 0)
        fprintf(file, ",W=%u", se->se_width);
      if (se->se_unit != NULL)
        fprintf(file, ",U=%s", se->se_unit);
      if (se->se_desc != NULL)
        fprintf(file, ",D=%s", se->se_desc);
      fprintf(file, ";");
    }
    fprintf(file, "\n");
  }

  return 0;
}

void stats_type_wr_stats(struct stats_type *type, FILE *file)
{
  size_t i = 0;
  struct dict_entry *de;
  while ((de = dict_for_each(&type->st_current_dict, &i)) != NULL) {
    struct stats *stats = (struct stats *) de->d_key - 1; /* XXX */

    fprintf(file, "%s %s", type->st_name, stats->s_dev);

    int j;
    for (j = 0; j < type->st_schema.sc_len; j++)
      fprintf(file, " %llu", stats->s_val[j]);

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
