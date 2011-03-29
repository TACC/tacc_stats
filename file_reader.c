#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <limits.h>
#include "stats.h"
#include "stats_file.h"
#include "trace.h"

typedef unsigned long long val_t;

#define SPACE_CHARS " \t\n\v\f\r"

struct stats_file_rd_ops {
  int (*o_set_schema)(const char *name, char *str);
  int (*o_set_devices)(const char *name, char *str);
  int (*o_set_variable)(const char *name, char *str);
  int (*o_set_property)(const char *name, char *str);
  int (*o_set_record)(const char *name, time_t time, const char *dev, val_t *rec, size_t len);
};

/* TODO Check white space skipping. */

static int parse_rec(val_t **p_buf, size_t *p_len, char *str)
{
  int i;
  val_t *buf = *p_buf;
  size_t len = *p_len;

  if (buf == NULL || len == 0) {
    len = 512;
    buf = malloc(len * sizeof(*buf));
    if (buf == NULL) {
      ERROR("cannot allocate record buffer: %m\n");
      return -1;
    }
  }

  for (i = 0; *str != 0; i++) {
    char *eov = str;
    val_t val = strtoull(str, &eov, 0); /* XXX Check for ERANGE. */

    if (eov == str) /* No digits. */
      goto out;

    if (i >= len) {
      size_t new_len = 2 * len;
      val_t *new_buf = realloc(buf, new_len * sizeof(*buf));
      if (new_buf == NULL) {
        ERROR("cannot allocate record buffer: %m\n");
        goto out;
      }
      len = new_len;
      buf = new_buf;
    }

    buf[i] = val;
    str = eov;
  }

 out:
  *p_buf = buf;
  *p_len = len;
  return i;
}

int stats_file_rd(FILE *file, const char *path, struct stats_file_rd_ops *ops)
{
  int rc = 0;
  char *line_buf = NULL, *line;
  size_t line_buf_size = 0;
  val_t *rec_buf = NULL;
  size_t rec_buf_len = 0;

  /* Header. */
  int nr = 0;
  while (getline(&line_buf, &line_buf_size, file) > 0) {
    nr++;
    line = line_buf;

    while (isspace(*line))
      line++;

    if (*line == 0)
      break; /* End of header. */

    int (*op)(const char *, char *) = NULL;
    int c = *(line++);
    switch (c) {
    default:
      ERROR("%s:%d: bad directive `%c%s'\n", path, nr, c, line);
      goto err;
    case '!':
      op = ops->o_set_schema;
      goto do_op;
    case '@':
      op = ops->o_set_devices;
      goto do_op;
    case '#':
      continue;
    case '$':
      op = ops->o_set_variable;
      continue;
    case '%':
      op = ops->o_set_property;
      goto do_op;
    }

  do_op:
    if (op == NULL)
      continue;

    char *name = strsep(&line, SPACE_CHARS);
    if (*name == 0 || line == NULL) {
      /* Weird line. */
      continue;
    }

    if ((*op)(name, line) < 0)
      goto err;
  }

  /* End of header. */
  if (ops->o_set_record == NULL)
    goto out;

  time_t time = 0;
  while (getline(&line_buf, &line_buf_size, file) > 0) {
    const char *name, *dev;

    nr++;
    line = line_buf;

    while (isspace(*line))
      line++;

    if (isdigit(*line)) {
      time = strtol(line, NULL, 0);
      continue;
    }

    name = strsep(&line, SPACE_CHARS);
    if (*name == 0 || line == NULL)
      continue;

    dev = strsep(&line, SPACE_CHARS);
    if (*dev == 0 || line == NULL)
      continue;

    int rec_len = parse_rec(&rec_buf, &rec_buf_len, line);
    if (rec_len < 0)
      continue;

    if ((*ops->o_set_record)(name, time, dev, rec_buf, rec_len) < 0)
      goto err;
  }

  if (ferror(file)) {
 err:
    rc = -1;
    if (errno == 0)
      errno = EINVAL;
  }

 out:
  if (ferror(file))
    ERROR("error reading from `%s': %m\n", path);

  free(line_buf);
  free(rec_buf);
  return rc;
}
