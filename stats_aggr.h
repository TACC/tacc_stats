#ifndef _STATS_AGGR_H_
#define _STATS_AGGR_H_
#include <stddef.h>
#include <time.h>

#define SF_WIDTH 0xFF
#define SF_EVENT 0x100
#define SF_RESOURCE 0x200
#define SF_CONTROL 0x1000
#define SF_STATUS 0x2000
#define sf_is_scalar(f) (((f) & (SF_CONTROL|SF_STATUS)) == 0)
#define sf_is_event(f) (((f) & SF_EVENT) == SF_EVENT)
#define sf_width(f) ((f) & SF_WIDTH)

struct stats_type;
typedef unsigned long long val_t;

struct stats_aggr {
  val_t *sa_buf;
  val_t *sa_base_rec;
  val_t *sa_prev_rec;
  val_t *sa_cur_rec; /* Initialized to sa_buf. */
  unsigned int *sa_flags;
  time_t sa_begin, sa_end, sa_step;
  time_t sa_prev_time; /* Initialized to -1 */
  time_t sa_cur_time; /* Initialized to sa_begin. */
  size_t sa_rec_len;
};

int stats_aggr_init(struct stats_aggr *sa, struct stats_type *type, time_t begin, time_t end, time_t step);
void stats_aggr(struct stats_aggr *sa, time_t time, const val_t *rec);
void stats_aggr_rewind(struct stats_aggr *sa);
void stats_aggr_sum(struct stats_aggr *r, const struct stats_aggr *s);
int stats_aggr_print(FILE *file, struct stats_aggr *sa, const char *time_fmt, const char *dev, const char *fs, const char *rs);

#endif
