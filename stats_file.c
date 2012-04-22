#include <stdio.h>
#include <stdlib.h>
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
#include "string1.h"

#define SF_SCHEMA_CHAR '!'
#define SF_DEVICES_CHAR '@'
#define SF_COMMENT_CHAR '#'
#define SF_PROPERTY_CHAR '$'
#define SF_MARK_CHAR '%'

#define sf_printf(sf, fmt, args...) fprintf(sf->sf_file, fmt, ##args)

static int sf_rd_hdr(struct stats_file *sf)
{
  int rc = 0;
  char *line_buf = NULL, *line;
  size_t line_buf_size = 0;

  if (getline(&line_buf, &line_buf_size, sf->sf_file) <= 0) {
    if (feof(sf->sf_file)) {
      sf->sf_empty = 1;
      goto out;
    }
    goto err;
  }

  line = line_buf;
  if (*(line++) != SF_PROPERTY_CHAR) {
    ERROR("file `%s' is not in %s format\n", sf->sf_path, STATS_PROGRAM);
    goto err;
  }

  char *prog = wsep(&line);
  if (prog == NULL || strcmp(prog, STATS_PROGRAM) != 0) {
    ERROR("file `%s' is not in %s format\n", sf->sf_path, STATS_PROGRAM);
    goto err;
  }

  char *vers = wsep(&line);
  if (vers == NULL || strverscmp(vers, STATS_VERSION) > 0) {
    ERROR("file `%s' is has unsupported version `%s'\n", sf->sf_path, vers != NULL ? vers : "NULL");
    goto err;
  }

  TRACE("prog %s, vers %s\n", prog, vers);

  int nr = 1;
  while (getline(&line_buf, &line_buf_size, sf->sf_file) > 0) {
    nr++;
    line = line_buf;

    char *first = wsep(&line);
    if (first == NULL)
      break; /* End of header. */

    struct stats_type *type;
    TRACE("%s:%d: first `%s', rest `%s'\n", sf->sf_path, nr, first, line);
    switch (*first) {
    case SF_SCHEMA_CHAR:
      type = stats_type_get(first + 1);
      if (type == NULL) {
        ERROR("%s:%d: unknown type `%s'\n", sf->sf_path, nr, first + 1);
        goto err;
      }
      type->st_schema_def = strdup(line);
      type->st_enabled = 1;
      break;
    case SF_DEVICES_CHAR: /* TODO. */
      break;
    case SF_COMMENT_CHAR:
      break;
    case SF_PROPERTY_CHAR:
      break;
    case SF_MARK_CHAR:
      break;
    default:
      ERROR("%s:%d: bad directive `%s %s'\n", sf->sf_path, nr, first, line);
      goto err;
    }
  }

 out:
  if (ferror(sf->sf_file)) {
  err:
    rc = -1;
    if (errno == 0)
      errno = EINVAL;
  }

  if (ferror(sf->sf_file))
    ERROR("error reading from `%s': %m\n", sf->sf_path);

  free(line_buf);
  return rc;
}

static int sf_wr_hdr(struct stats_file *sf)
{
  struct utsname uts_buf;
  unsigned long long uptime = 0;

  uname(&uts_buf);
  pscanf("/proc/uptime", "%llu", &uptime);

  sf_printf(sf, "%c%s %s\n", SF_PROPERTY_CHAR, STATS_PROGRAM, STATS_VERSION);

  sf_printf(sf, "%chostname %s\n", SF_PROPERTY_CHAR, uts_buf.nodename);
  sf_printf(sf, "%cuname %s %s %s %s\n", SF_PROPERTY_CHAR, uts_buf.sysname,
            uts_buf.machine, uts_buf.release, uts_buf.version);
  sf_printf(sf, "%cuptime %llu\n", SF_PROPERTY_CHAR, uptime);

  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (!type->st_enabled)
      continue;

    TRACE("type %s, schema_len %zu\n", type->st_name, type->st_schema.sc_len);

    /* Write schema. */
    sf_printf(sf, "%c%s", SF_SCHEMA_CHAR, type->st_name);

    /* MOVEME */
    size_t j;
    for (j = 0; j < type->st_schema.sc_len; j++) {
      struct schema_entry *se = type->st_schema.sc_ent[j];
      sf_printf(sf, " %s", se->se_key);
      if (se->se_type == SE_CONTROL)
        sf_printf(sf, ",C");
      if (se->se_type == SE_EVENT)
        sf_printf(sf, ",E");
      if (se->se_unit != NULL)
        sf_printf(sf, ",U=%s", se->se_unit);
      if (se->se_width != 0)
        sf_printf(sf, ",W=%u", se->se_width);
    }
    sf_printf(sf, "\n");
  }

  fflush(sf->sf_file);

  return 0;
}

int stats_file_open(struct stats_file *sf, const char *path)
{
  int rc = 0;
  memset(sf, 0, sizeof(*sf));

  sf->sf_path = strdup(path);
  if (sf->sf_path == NULL) {
    ERROR("cannot create path: %m\n");
    goto err;
  }

  /* modified by charngda, Jan 11, 2012 */
  /* On the old Myrinet/Pentium 4 nodes, e.g. f13n11,
     if STDIN is closed (as in daemon mode), then
     fopen here will return STDIN, i.e. 0. This causes
     trouble later when doing seek and write to
     sf->sf_file ("bad file descriptor") in stats_file_close().
     Hence, we keep trying fopen until fopen returns a
     file descriptor larger than STDERR, i.e. 2.
   */
  int tmpfds[STDERR_FILENO+1] = {0};
  while (1) {
    sf->sf_file = fopen(sf->sf_path, "a+");
    if (sf->sf_file == NULL) {
      ERROR("cannot open `%s': %m\n", path);
      goto err;
    }
    if (STDERR_FILENO < fileno(sf->sf_file)) {
      int i;
      for (i=0; i <=STDERR_FILENO; ++i) {
        if (tmpfds[i]) close(i);
      }
      break;
    }
    else {
      tmpfds[fileno(sf->sf_file)]=1;
    }
  }

  if (sf_rd_hdr(sf) < 0) {
 err:
    rc = -1;
  }

  return rc;
}

int stats_file_mark(struct stats_file *sf, const char *fmt, ...)
{
  char *s = NULL;

  va_list args;
  va_start(args, fmt);
  vasprintf(&s, fmt, args);
  va_end(args);
  if (s) {
    if (NULL == sf->sf_mark) {
      sf->sf_mark = s;
    }
    else {
      /* Concatenate new mark with old, using "\xff" as delimiter */
      char *t = NULL;
      if (0<asprintf(&t, "%s\xff%s", sf->sf_mark,s)) {
        free(sf->sf_mark);
        sf->sf_mark = t;
      }
      free(s);
    }
  }
  else {
    sf->sf_mark = NULL;
  }
  return 0;
}

int stats_file_close(struct stats_file *sf)
{
  int rc = 0;

  if (sf->sf_empty)
    sf_wr_hdr(sf);

  fseek(sf->sf_file, 0, SEEK_END);

  sf_printf(sf, "\n%ld %s\n", (long) current_time, current_jobid);

  /* Write mark. */
  if (sf->sf_mark) {
    char *s = strdup(sf->sf_mark);
    char *orig = s;
    while (*s) {
      if ('\n'==*s) *s=' ';
      ++s;
    }
    /* marks are delimitered by "\xff" */
    s = strtok(orig,"\xff");
    while (s) {
      sf_printf(sf, "%c %s\n", SF_MARK_CHAR,s);
      s = strtok(NULL,"\xff");
    }
    free(orig);
  }

  /* Write stats. */
  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (!(type->st_enabled && type->st_selected))
      continue;

    size_t j = 0;
    char *dev;
    while ((dev = dict_for_each(&type->st_current_dict, &j)) != NULL) {
      struct stats *stats = key_to_stats(dev);

      sf_printf(sf, "%s %s", type->st_name, stats->s_dev);

      size_t k;
      for (k = 0; k < type->st_schema.sc_len; k++)
        sf_printf(sf, " %llu", stats->s_val[k]);

      sf_printf(sf, "\n");
    }
  }

  if (ferror(sf->sf_file)) {
    ERROR("error writing to `%s': %m\n", sf->sf_path);
    rc = -1;
  }

  if (fclose(sf->sf_file) < 0) {
    ERROR("error closing `%s': %m\n", sf->sf_path);
    rc = -1;
  }
  free(sf->sf_path);
  free(sf->sf_mark);
  memset(sf, 0, sizeof(struct stats_file));

  return rc;
}
