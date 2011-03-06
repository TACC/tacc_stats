#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <limits.h>
#include "stats.h"
#include "trace.h"

struct stats_file {
  FILE *sf_file;
  const char *sf_path;
};

int stats_file_rd_hdr(struct stats_file *file)
{
  int rc = -1;
  char *buf = NULL;
  size_t size = 0;
  int nr = 0;

  int len;
  while ((len = getline(&buf, &size, file->sf_file)) > 0) {
    char *line = buf;
    nr++;

    /* Check for and remove newline. */
    if (line[len - 1] != '\n') {
      ERROR("%s:%d: unexpected end of file\n", file->sf_path, nr);
      goto out;
    }

    line[len - 1] = 0;
    len--;

    /* Empty line means end of header. */
    if (len <= 0)
      goto end_of_hdr;

    /* First line must be "tacc_stats VERSION". */
    if (nr == 1) {
      char *prog = strsep(&line, " "), *vers = strsep(&line, " ");
      if (prog == NULL || strcmp(prog, TACC_STATS_PROGRAM) != 0) {
        ERROR("file `%s' is not in %s format\n", file->sf_path, TACC_STATS_PROGRAM);
        goto out;
      }
      if (vers == NULL || strverscmp(vers, TACC_STATS_VERSION) > 0) {
        ERROR("file `%s' is has unsupported version `%s'\n", file->sf_path, vers != NULL ? vers : "NULL");
        goto out;
      }
      continue;
    }

    /* TODO Jobid in header. */
    /* Check for change of job. */

    int c = *(line++);

    if (c == '$') {
      if (tacc_stats_config(line) < 0)
        goto out;
      continue;
    }

    char *name = strsep(&line, " ");
    if (*name == 0 || line == NULL) {
      line = "";
      ERROR("%s:%d: bad directive `%c%s %s'\n", file->sf_path, nr, c, name, line);
      goto out;
    }

    struct stats_type *type = name_to_type(name);
    if (type == NULL) {
      ERROR("%s:%d: unknown type `%s'\n", file->sf_path, nr, name);
      goto out;
    }

    TRACE("%s:%d: %c %s %s\n", file->sf_path, nr, c, name, line);
    switch (c) {
    case '.':
      if (stats_type_config(type, line) < 0)
        goto out;
      break;
    case '!':
      if (stats_type_set_schema(type, line) < 0)
        goto out;
      break;
    case '@':
      if (stats_type_set_devices(type, line) < 0)
        goto out;
      break;
    case '#':
      break;
    default:
      ERROR("%s:%d: bad directive %c%s %s\n", file->sf_path, nr, c, name, line);
      goto out;
    }
  }

  if (ferror(file->sf_file)) {
    ERROR("error reading from `%s': %m\n", file->sf_path);
    goto out;
  }

 end_of_hdr:
  if (nr > 0)
    rc = 0;

 out:
  free(buf);

  return rc;
}
