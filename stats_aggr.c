#include <errno.h>
#include <stddef.h>
#include <malloc.h>
#include <string.h>
#include <time.h>
#include "stats.h"
#include "stats_aggr.h"
#include "trace.h"

/* Consider including back pointer to type or dev. */

#define sa_rec_size(sa) ((sa)->sa_rec_len * sizeof(val_t))

int stats_aggr_init(struct stats_aggr *sa, struct stats_type *type, time_t begin, time_t end, time_t step)
{
  size_t nr_rec, rec_len;
  memset(sa, 0, sizeof(*sa));

  if (begin < 0 || end < 0 || step <= 0) {
    errno = EINVAL;
    goto err;
  }

  nr_rec = (end - begin + step - 1) / step;
  rec_len = 1; /* XXX */

  TRACE("nr_rec %zu, rec_len %zu\n", nr_rec, rec_len);

  sa->sa_buf = calloc(nr_rec * rec_len, sizeof(*sa->sa_buf));
  if (sa->sa_buf == NULL)
    goto err;
  sa->sa_base_rec = calloc(rec_len, sizeof(*sa->sa_base_rec));
  if (sa->sa_base_rec == NULL)
    goto err;
  sa->sa_prev_rec = calloc(rec_len, sizeof(*sa->sa_prev_rec));
  if (sa->sa_prev_rec == NULL)
    goto err;
  sa->sa_flags = calloc(rec_len, sizeof(*sa->sa_flags));
  if (sa->sa_flags == NULL)
    goto err;

  sa->sa_cur_rec = sa->sa_buf;
 /* Init flags. */
  sa->sa_begin = begin;
  sa->sa_end = end;
  sa->sa_step = step;
  sa->sa_prev_time = -1;
  sa->sa_cur_time = sa->sa_begin;
  sa->sa_rec_len = rec_len;
  return 0;

 err:
  ERROR("cannot initialize struct stats_aggr: %m\n");
  free(sa->sa_buf);
  free(sa->sa_flags);
  free(sa->sa_base_rec);
  free(sa->sa_prev_rec);
  return -1;
}

/* TODO Consider averaging resource counters when a single step spans
   multiple samples. */

void stats_aggr(struct stats_aggr *sa, time_t time, const val_t *rec)
{
  int i;

  if (sa->sa_prev_time == (time_t) -1) {
    for (i = 0; i < sa->sa_rec_len; i++) {
      if (sf_is_event(sa->sa_flags[i]))
        sa->sa_base_rec[i] = rec[i];
    }

    sa->sa_prev_time = 0;
    memmove(sa->sa_prev_rec, rec, sa_rec_size(sa));
  }

  /* Ignore out of order times, but produce an error message. */
  if (time < sa->sa_prev_time) {
    ERROR("out of order records time %ld, prev_time %ld\n", time, sa->sa_prev_time);
    return;
  }

  /* Overwrite on multiple samples for a given time. */
  if (time == sa->sa_prev_time)
    goto out;

  if (time < sa->sa_begin)
    goto out;

  /* Try to handle wrap on event counters. */
  for (i = 0; i < sa->sa_rec_len; i++) {
    if (!sf_is_event(sa->sa_flags[i]))
      continue;

    if (rec[i] >= sa->sa_prev_rec[i])
      continue;

    unsigned int width = sf_width(sa->sa_flags[i]);
    TRACE("wrap detected, i %d, prev_time %ld, time %ld, width %d\n", i, sa->sa_prev_time, time, width);
    if (width == 0) {
      ERROR("wrap detected on full width counter %d, time %ld\n", i, time); /* ... */
      /* TODO Figure out what to do here.  Maybe assume counter was
         reset and adjust base accordingly. */
      continue;
    }

    sa->sa_base_rec[i] -= (val_t) 1 << width;
  }

  while (sa->sa_cur_time < sa->sa_end && sa->sa_cur_time <= time) {
    for (i = 0; i < sa->sa_rec_len; i++) {
      if (!sf_is_scalar(sa->sa_flags[i])) {
        /* Don't interpolate bits,... */
        sa->sa_cur_rec[i] = sa->sa_prev_rec[i];
        continue;
      }

      sa->sa_cur_rec[i] = sa->sa_prev_rec[i] - sa->sa_base_rec[i]
        + (long long) (rec[i] - sa->sa_prev_rec[i])
        * (sa->sa_cur_time - sa->sa_prev_time)
        / (time - sa->sa_prev_time);
    }
    sa->sa_cur_time += sa->sa_step;
    sa->sa_cur_rec += sa->sa_rec_len;
  }

 out:
  sa->sa_prev_time = time;
  memmove(sa->sa_prev_rec, rec, sa_rec_size(sa));
}

void stats_aggr_rewind(struct stats_aggr *sa)
{
  if (sa->sa_prev_time == (time_t) -1)
    return;

  if (sa->sa_prev_time < sa->sa_end)
    stats_aggr(sa, sa->sa_end, sa->sa_prev_rec);

  sa->sa_cur_time = sa->sa_begin;
  sa->sa_cur_rec = sa->sa_buf;
  sa->sa_prev_time = -1;
  memset(sa->sa_prev_rec, 0, sa_rec_size(sa));
}

void stats_aggr_sum(struct stats_aggr *r, const struct stats_aggr *s)
{
  time_t time = r->sa_begin;
  time_t end = r->sa_end;
  time_t step = r->sa_step;
  val_t *r_rec = r->sa_buf;
  const val_t *s_rec = s->sa_buf;

  /* TODO Sanity checking. */
  int i;
  for (; time < end; time += step, r_rec += r->sa_rec_len, s_rec += s->sa_rec_len)
    for (i = 0; i < r->sa_rec_len; i++)
      if (sf_is_scalar(r->sa_flags[i]))
        r_rec[i] += s_rec[i];
}

int stats_aggr_print(FILE *file, struct stats_aggr *sa, const char *time_fmt, const char *dev, const char *fs, const char *rs)
{
  time_t time, end, step;
  const val_t *rec, *val;

  time = sa->sa_begin;
  end = sa->sa_end;
  step = sa->sa_step;
  rec = sa->sa_buf;

  for (; time < end; time += step, rec += sa->sa_rec_len) {
    int nf = 0;

    if (time_fmt != NULL) {
      char time_buf[80]; /* XXX */
      struct tm tm;

      *time_buf = 0;
      localtime_r(&time, &tm);
      strftime(time_buf, sizeof(time_buf), time_fmt, &tm);
      fprintf(file, "%s", time_buf);
      nf++;
    }

    if (dev != NULL) {
      fprintf(file, "%s%s", nf == 0 ? "" : fs, dev);
      nf++;
    }

    for (val = rec; val < rec + sa->sa_rec_len; val++) {
      fprintf(file, "%s%llu", nf == 0 ? "" : fs, *val);
      nf++;
    }

    fprintf(file, "%s", rs);
  }

  return 0;
}
