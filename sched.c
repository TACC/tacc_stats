#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <unistd.h>
#include "stats.h"
#include "trace.h"
#include "string1.h"

/*
   Support for /proc/schedstat
   (see sched_stats.h or sched.c or
   Documentation/scheduler/sched-stats.txt or
   search
   for "SCHEDSTAT_VERSION" in the Linux kernel source
   tree)

   Also see http://eaglet.rain.com/rick/linux/schedstat/
*/

/* Processor core runqueue stats */
#define CPU_STATS \
    X(yld_count, "E", ""), \
    X(sched_switch, "E", ""), \
    X(sched_count, "E", ""), \
    X(sched_goidle, "E", ""), \
    X(ttwu_count, "E", ""), \
    X(ttwu_local, "E", ""), \
    X(running_time, "E,U=ms", ""), \
    X(waiting_time, "E,U=ms", ""), \
    X(pcount, "E", "")

/* SMP scheduling domains: load balacing stats */
#define LB_STATS(dom) Y(dom,idle),Y(dom,busy),Y(dom,just_idle)
#define Y(dom,x) \
    X(Z(dom,lb_##x##_count), "E", ""), \
    X(Z(dom,lb_##x##_balanced), "E", ""), \
    X(Z(dom,lb_##x##_failed), "E", ""), \
    X(Z(dom,lb_##x##_imbalance), "E", ""), \
    X(Z(dom,lb_##x##_gained), "E", ""), \
    X(Z(dom,lb_##x##_hot_gained), "E", ""), \
    X(Z(dom,lb_##x##_nobusyq), "E", ""), \
    X(Z(dom,lb_##x##_nobusyg), "E", "")

/* SMP scheduling domains: try-to-wake-up stats, part 1: Active load balancing */
#define TTWU_STATS1(dom) \
    X(Z(dom,alb_count), "E", ""), \
    X(Z(dom,alb_failed), "E", ""), \
    X(Z(dom,alb_pushed), "E", "")

/* SMP scheduling domains: try-to-wake-up stats, part 2: Passive load balancing */
#define TTWU_STATS2(dom) \
    X(Z(dom,ttwu_wake_remote), "E", ""), \
    X(Z(dom,ttwu_move_affine), "E", ""), \
    X(Z(dom,ttwu_move_balance), "E", "")

#define Z(d,label) dom##d##label

#define DOM_STATS(dom) LB_STATS(dom),TTWU_STATS1(dom),TTWU_STATS2(dom)

/* At most three scheduling domains: HyperThreading (virtual) cores,
   physical cores in a socket, and all sockets in a compute node */
#define KEYS CPU_STATS,DOM_STATS(0),DOM_STATS(1),DOM_STATS(2)

/**************************************/
static void stats_set_wrapper( struct stats *stats, int domain, const char *key, unsigned long long val ) {
    /*  If key is like "dom_lb_idle_count", replace the first
        underscore by "domain", which should be a single digit.

        This is a helper function used by collect_sched
     */
    char s[1024];
    if ( 0 > domain || 10 < domain ) return;
    char *t = strchr( key, '_' );
    if ( NULL == t ) return;
    strcpy( s, key );
    s[t - key] = '0' + domain;
    /*  insert the metric value using the new key */
    stats_set( stats, s, val );
}

/**************************************/
static void collect_sched( struct stats_type *type ) {
    FILE *file = NULL;
    char *line = NULL;
    size_t line_size = 0;
    static int version = 0;
    static char *cpufmt = NULL;
    char *path = "/proc/schedstat";
    struct stats *stats = NULL;

    file = fopen( path, "r" );
    if ( file == NULL ) {
        ERROR( "cannot open `%s': %m\n", path );
        goto out;
    }

    while ( 0 <= getline( &line, &line_size, file ) ) {
        if ( !version ) {
            if ( 1 == sscanf( line, "version %d", &version ) ) {
                /* only versions 12,14,15 are supported */
                if ( 15 < version  || 12 > version ) break;
            }
        }
        else {
            int domain;
            char *rest = line;
            char *key = wsep( &rest );

            if ( key == NULL || rest == NULL )
                continue;

            if  ( !strncasecmp( key, "cpu", 3 ) ) {
                if ( NULL == cpufmt ) {
                    char *skiplist = "";
                    if ( 15 > version ) {
                        /* skip the first 3 fields since they
                           only exist in version 12 & 14 */
                        skiplist = "%*s %*s %*s ";
                    }
#define X(k,r...) "%llu "
                    asprintf( &cpufmt, "%s %s ", skiplist, JOIN( CPU_STATS ) );
#undef X
                }
                if ( NULL == cpufmt ) break;
                stats = get_current_stats( type, key + 3 );
                if ( NULL ==  stats ) break;

#define X(k,r...) k = 0
                unsigned long long CPU_STATS;
#undef X
#define X(k,r...) &k
                sscanf( rest, cpufmt, CPU_STATS );
#undef X
#define X(k,r...) stats_set(stats, #k, k)
                //#define X(k,r...) printf( #k " is %llu\n", k)
                CPU_STATS;
#undef X
            }
            else if ( 1 == sscanf( key, "domain%d", &domain ) && NULL != stats ) {
#define X(k,r...) k = 0
                unsigned long long DOM_STATS( _ );
#undef X
                /* skip the CPU mask string as well as six metrics
                   which are always 0, as mentioned in
                   http://eaglet.rain.com/rick/linux/schedstat/
                 */
                if ( 1 < sscanf( rest,
#define X(k,r...) "%llu "
                                 "%*s "
                                 JOIN( LB_STATS( _ ) )
                                 JOIN( TTWU_STATS1( _ ) )
                                 "%*s %*s %*s %*s %*s %*s "
                                 JOIN( TTWU_STATS2( _ ) )
#undef X
#define X(k,r...) &k
                                 , DOM_STATS( _ ) ) )
#undef X
                {
#define STRINGIFY(k) #k
#define X(k,...) stats_set_wrapper(stats,domain, STRINGIFY(k), k)
                    DOM_STATS( _ );
#undef X

                }
            }
        }
    }
out:
    if ( NULL != line )
        free( line );
    if ( NULL != file )
        fclose( file );
}

struct stats_type sched_stats_type = {
    .st_name = "sched",
    .st_collect = &collect_sched,
#define X(k,o,d,r...) SCHEMA_DEF(k,o,d,r...)
    .st_schema_def = JOIN( KEYS ),
#undef X
};
