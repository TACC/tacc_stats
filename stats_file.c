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
#include "pscanf.h"

#define sf_printf(sf, fmt, args...) fprintf(sf->sf_file, fmt, ##args)

#define SPACE_CHARS " \t\n\v\f\r"

int stats_file_rd_hdr(struct stats_file *sf)
{
  int rc = 0;
  char *buf = NULL, *line;
  size_t size = 0;

  if (getline(&buf, &size, sf->sf_file) <= 0) {
    if (feof(sf->sf_file))
      ERROR("empty stats file `%s'\n", sf->sf_path);
    goto err;
  }

  line = buf;
  if (*(line++) != '#') {
    ERROR("file `%s' is not in %s format\n", sf->sf_path, TACC_STATS_PROGRAM);
    goto err;
  }

  char *prog = strsep(&line, SPACE_CHARS);
  if (prog == NULL || strcmp(prog, TACC_STATS_PROGRAM) != 0) {
    ERROR("file `%s' is not in %s format\n", sf->sf_path, TACC_STATS_PROGRAM);
    goto err;
  }

  char *vers = strsep(&line, SPACE_CHARS);
  if (vers == NULL || strverscmp(vers, TACC_STATS_VERSION) > 0) {
    ERROR("file `%s' is has unsupported version `%s'\n", sf->sf_path, vers != NULL ? vers : "NULL");
    goto err;
  }

  TRACE("prog %s, vers %s\n", prog, vers);

  /* TODO Jobid in header. */
  /* TODO Ignore whitespace. */

  int nr = 1;
  while (getline(&buf, &size, sf->sf_file) > 0) {
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
      ERROR("%s:%d: bad directive `%c%s %s'\n", sf->sf_path, nr, c, name, line);
      goto err;
    }

    struct stats_type *type = name_to_type(name);
    if (type == NULL) {
      ERROR("%s:%d: unknown type `%s'\n", sf->sf_path, nr, name);
      goto err;
    }

    TRACE("%s:%d: c %c, name %s, rest %s\n", sf->sf_path, nr, c, name, line);
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
      ERROR("%s:%d: bad directive `%c%s %s'\n", sf->sf_path, nr, c, name, line);
      goto err;
    }
  }

  if (ferror(sf->sf_file)) {
  err:
    rc = -1;
    if (errno == 0)
      errno = EINVAL;
  }

  if (ferror(sf->sf_file))
    ERROR("error reading from `%s': %m\n", sf->sf_path);

  free(buf);

  return rc;
}

int stats_file_wr_hdr(struct stats_file *sf)
{
  struct utsname uts_buf;
  unsigned long long uptime = 0;

  uname(&uts_buf);
  pscanf("/proc/uptime", "%llu", &uptime);

  sf_printf(sf, "#%s %s\n", TACC_STATS_PROGRAM, TACC_STATS_VERSION);
  /* Make these global properties. */
  sf_printf(sf, "$hostname %s\n", uts_buf.nodename);
  sf_printf(sf, "$uname %s %s %s %s\n", uts_buf.sysname, uts_buf.machine,
          uts_buf.release, uts_buf.version);
  sf_printf(sf, "$uptime %llu\n", uptime);

  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (!type->st_enabled)
      continue;

    TRACE("type %s, schema_len %zu\n", type->st_name, type->st_schema.sc_len);

    /* Write schema. */
    sf_printf(sf, "!%s", type->st_name);

    /* MOVEME */
    size_t j;
    for (j = 0; j < type->st_schema.sc_len; j++) {
      struct schema_entry *se = type->st_schema.sc_ent[j];
      sf_printf(sf, " %s%s%s", se->se_key,
              se->se_type == SE_EVENT ? ",E" : "",
              se->se_type == SE_BITS ? ",B" : "");
      if (se->se_width != 0)
        sf_printf(sf, ",W=%u", se->se_width);
      if (se->se_unit != NULL)
        sf_printf(sf, ",U=%s", se->se_unit);
      if (se->se_desc != NULL)
        sf_printf(sf, ",D=%s", se->se_desc);
      sf_printf(sf, ";");
    }
    sf_printf(sf, "\n");
  }

  fflush(sf->sf_file);

  return 0;
}

static void stats_type_wr_stats(struct stats_file *sf, struct stats_type *type)
{
  size_t i = 0;
  struct dict_entry *de;
  while ((de = dict_for_each(&type->st_current_dict, &i)) != NULL) {
    struct stats *stats = key_to_stats(de->d_key);

    sf_printf(sf, "%s %s", type->st_name, stats->s_dev);

    int j;
    for (j = 0; j < type->st_schema.sc_len; j++)
      sf_printf(sf, " %llu", stats->s_val[j]);

    sf_printf(sf, "\n");
  }
}

int stats_file_wr_rec(struct stats_file *sf)
{
  fseek(sf->sf_file, 0, SEEK_END);

  sf_printf(sf, "\n%ld\n", (long) current_time);

  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL)
    if (type->st_enabled && type->st_selected)
      stats_type_wr_stats(sf, type);

  fflush(sf->sf_file);

  return 0;
}

int stats_file_wr_mark(struct stats_file *sf, const char *str)
{
  fseek(sf->sf_file, 0, SEEK_END);

  while (*str != 0) {
    const char *eol = strchrnul(str, '\n');
    sf_printf(sf, "^%*s\n", (int) (eol - str), str);
    str = eol;
    if (*str == '\n')
      str++;
  }

  fflush(sf->sf_file);

  return 0;
}
