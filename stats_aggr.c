
typedef unsigned long long val_t;

struct stats_aggr {
  val_t *sa_buf;
  size_t sa_rec_len;
  int *sa_flags;
  time_t sa_begin, sa_end, sa_step;

  val_t *sa_base_rec;
  time_t sa_prev_time; /* -1 */
  val_t *sa_prev_rec;

  size_t sa_cur_time; /* Initialized to sa_begin. */
  val_t *sa_cur_rec; /* Initialized to sa_buf. */
};

int stats_aggr_init(struct stats_aggr *sa, struct stats_type *type, time_t begin, time_t end, time_t step)
{
  size_t nr_rec, rec_len;

  /* XXX */
  nr_rec = (end - begin) / step;
  memset(sa, 0, sizeof(*sa));

  sa->sa_rec_len = rec_len;

  sa->sa_buf = calloc(nr_rec * sa->sa_rec_len, sizeof(val_t));
  sa->sa_flags = calloc(sa->sa_rec_len, sizeof(val_t));
  sa->sa_base_rec = calloc(sa->sa_rec_len, sizeof(val_t));
  sa->sa_prev_rec = calloc(sa->sa_rec_len, sizeof(val_t));

  /* Init flags. */

  sa->sa_cur_rec = sa->sa_buf;
  sa->sa_cur_time = sa->sa_begin;
  sa->sa_prev_time = -1;

  return 0;

 err:
  free(sa->sa_buf);
  free(sa->sa_flags);
  free(sa->sa_base_rec);
  free(sa->sa_prev_rec);
  return -1;
}

void stats_aggr(struct stats_aggr *sa, time_t time, const val_t *rec)
{
  if (sa->sa_prev_time == (time_t) -1) {
    int i;
    for (i = 0; i < sa->sa_rec_len; i++) {
      if (sa->sa_flags[i] & SA_F_EVENT)
        sa->sa_base_rec[i] = rec[i];
    }

    sa->sa_prev_time = 0;
    memcpy(sa->sa_prev_rec, sa_rec_size(sa), rec);
  }

  /* Ignore out of order times, but produce an error message. */
  if (time < sa->sa_prev_time) {
    ERROR("out of order records\n");
    return;
  }

  /* Overwrite on duplicate times, don't add. */
  if (time == sa->sa_prev_time)
    goto out;

  if (time < sa->sa_begin)
    goto out;

  while (sa->sa_cur_time < sa->sa_end && sa->sa_cur_time <= time) {
    int i;
    for (i = 0; i < sa->sa_rec_len; i++) {
      if (sa->sa_flags[i] & SA_F_CONTROL) {
        sa->sa_cur_rec[i] = sa->sa_prev_rec[i];
        continue;
      }

      if ((sa->sa_flags[i] & SA_F_EVENT) && rec[i] < sa->sa_prev_rec[i]) {
        int width = sa->sa_flags[i] & SA_F_WIDTH;
        if (width == 0) {
          ERROR("wrap detected on full width counter\n"); /* ... */
          /* Hmm, maybe assume counter was reset and adjust base
             accordingly. */
        } else {
          TRACE("wrap detected, width %d\n", width); /* ... */

          sa->sa_base_rec[i] -= (val_t) 1 << width;
        }
      }

      sa->sa_cur_rec[i] = sa->sa_prev_rec[i] - sa->sa_base_rec[i]
        + (rec[i] - sa->sa_prev_rec[i])
        * (sa->sa_cur_time - sa->sa_prev_time)
        / (time - sa->sa_prev_time);
    }
    sa->sa_cur_time += sa->sa_step;
    sa->sa_cur_rec += sa_rec_size(sa);
  }

 out:
  sa->sa_prev_time = time;
  memcpy(sa->sa_prev_rec, sa_rec_size(sa), rec);
}

void stats_aggr_rewind(struct stats_aggr *sa)
{
  if (sa->sa_prev_time == (time_t) -1)
    return;

  stats_aggr(sa, sa->sa_end, sa->sa_prev_rec);
  sa->sa_cur_time = sa->sa_begin;
  sa->sa_cur_rec = sa->sa_buf;
  sa->sa_prev_time = -1;
  memset(sa->sa_prev_rec, 0, sa_rec_size(sa));
}
