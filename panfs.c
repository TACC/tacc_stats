#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <mntent.h>
#include <unistd.h>
#include <sys/statfs.h>
#include "stats.h"
#include "trace.h"
#include "string1.h"

#define PANFS_STAT_PATH "/usr/local/sbin/panfs_stat"

/*
   Support for the Panasas file system
 */

#define CLIENT_EXPORTED_OPSTATS \
    X(callback__breaks,"E",""),\
    X(callback__break_all,"E",""),\
    X(callback__cancels,"E",""),\
    X(ioctl__getattr,"E",""),\
    X(ioctl__setattr,"E",""),\
    X(op__device_create,"E",""),\
    X(op__dir_create,"E",""),\
    X(op__dir_delete,"E",""),\
    X(op__dir_fmlookup,"E",""),\
    X(op__dir_lookup,"E",""),\
    X(op__file_create,"E",""),\
    X(op__file_link_create,"E",""),\
    X(op__file_delete,"E",""),\
    X(op__file_rename,"E",""),\
    X(op__file_silly_rename,"E",""),\
    X(op__getattr_total,"E",""),\
    X(op__ioctl,"E",""),\
    X(op__llapi_sync,"E",""),\
    X(op__read,"E",""),\
    X(op__read__total_bytes,"E,U=B",""),\
    X(op__sync,"E",""),\
    X(op__sync__total_bytes,"E,U=B",""),\
    X(op__symlink_create,"E",""),\
    X(op__symlink_follow,"E",""),\
    X(op__symlink_read,"E",""),\
    X(op__setattr,"E",""),\
    X(op__write,"E",""),\
    X(op__write__total_bytes,"E,U=B",""),\
    X(op__write_retried,"E",""),\
    X(op__writepage,"E","")

#define SYSCALL_OPSTATS Y(close),Y(create),Y(fsync),Y(getattr),Y(getxattr),Y(ioctl),Y(link),Y(llseek),Y(lookup),Y(mkdir),Y(mmap),Y(open),Y(permission),Y(read),Y(readdir),Y(rename),Y(rmdir),Y(setattr),Y(statfs),Y(symlink),Y(unlink),Y(write)
#define Y(x) \
    X(syscall_##x##_suc, "E", ""), \
    X(syscall_##x##_uns, "E", ""), \
    X(syscall_##x##_suc_s, "E,U=s", ""), \
    X(syscall_##x##_uns_s, "E,U=s", ""), \
    X(syscall_##x##_suc_ns, "E,U=ns", ""), \
    X(syscall_##x##_uns_ns, "E,U=ns", "")

#define KEYS CLIENT_EXPORTED_OPSTATS,SYSCALL_OPSTATS,X(kernel_slab_size, "U=MB", "")


/**************************************/
static unsigned long long collect_slab_size() {
    /*
       Get information from /proc/slabinfo

       This code is adapted from the "slabtop" utility.
       See parse_slabinfo20() in slab.c from http://procps.sf.net
     */
    unsigned long long nr_slabs, pages_per_slab;
    unsigned long long slab_size = 0;
    char *line = NULL;
    size_t line_size = 0;
    FILE *file = fopen( "/proc/slabinfo", "r" );
    if ( NULL == file )
        return 0;

    if ( 0 > getline( &line, &line_size, file ) )
        goto out;

    if ( NULL == strstr( line, "slabinfo - version: 2" ) )
        goto out;

    while ( 0 <= getline( &line, &line_size, file ) ) {
        if ( strncasecmp( line, "pan_", 4 ) )
            continue;

        if ( 2 != sscanf( line, "%*s %*d %*d %*d %*d %llu : tunables %*d %*d %*d : slabdata %llu", &pages_per_slab, &nr_slabs ) )
            continue;
        slab_size += pages_per_slab * nr_slabs;

    }
    slab_size = slab_size * getpagesize() / 1024 / 1024;

out:
    if ( NULL != line )
        free( line );
    if ( NULL != file )
        fclose( file );
    return slab_size;
}

static void stats_set_wrapper( struct stats *stats, const char *key1, const char *key2, unsigned long long val ) {
    /*  If key1 is like "write" and key2 is like "syscall__suc",
        merge the two keys into "syscall_write_suc".

        This is a helper function used by collect_panfs_stats
     */
    char s[1024];
    char *t = strstr( key2, "__" );
    if ( NULL == t ) return;
    strcpy( s, key2 );
    s[t - key2 + 1] = '\0';
    strcat( s, key1 );
    strcat( s, t + 1 );
    /*  insert the metric value using the new key */
    stats_set( stats, s, val );
}

static void collect_panfs_stats( struct stats_type *type, const char *d_name, unsigned long long  slab_size  )  {
    char *cmd = NULL;
    FILE *file = NULL;
    char *line_buf = NULL;
    size_t line_buf_size = 0;

    struct stats *stats = get_current_stats( type, d_name );
    if ( NULL == stats ) return;
    stats_set( stats, "kernel_slab_size", slab_size );

    asprintf( &cmd, PANFS_STAT_PATH " %s", d_name );
    if ( NULL == cmd ) return;

    file = popen( cmd, "r" );
    if ( NULL == file ) {
        ERROR( "cannot execute `%s'\n", cmd );
        goto out;
    }

    while ( 0 <= getline( &line_buf, &line_buf_size, file ) ) {
        char *key, *tok, *rest = line_buf;
        unsigned long long metric;
        key = wsep( &rest );
        if ( key == NULL || rest == NULL )
            continue;
        if ( 1 == sscanf( rest, "%llu", &metric ) ) {
            // PanFS Client Exported Opstats
            //         callback__breaks        24189
            //         callback__break_all     0
            //         callback__cancels       25
            //         ioctl__getattr          0
            //         ioctl__setattr          0
            //         op__device_create       0
            //         op__dir_create          34
            //         op__dir_delete          21
            //         op__dir_fmlookup        75411
            stats_set( stats, key, metric );
            continue;
        }

        /* get next token */
        tok = wsep( &rest );
        if ( tok == NULL || rest == NULL )
            continue;
        if ( !strncasecmp( tok, "suc", 3 ) ) {
            // PanFS Syscall Opstats
            //         close       suc 16883 / unsuc     0 / started 16883  longest 0:060129066 / 0:000000000  avg 0:000073877 / 0:000000000
            //         create      suc  2168 / unsuc     0 / started  2168  longest 0:086021345 / 0:000000000  avg 0:002388346 / 0:000000000
#define X(k,r...) k = 0
            unsigned long long Y();
#undef X
            /* we want to know how many items in Y, but we cannot
               replace the commas by + in Y, so this is how we can
               get it (in dummyCnt) */
#define X(k,r...) k
            enum __dummyCnt { Y( __ ), dummyCnt};
#undef X
            if ( dummyCnt != sscanf( rest, "%llu %*s %*s %llu %*s %*s %*s longest %*s %*s %*s avg %llu:%llu %*s %llu:%llu",
#define X(k,r...) &k
                                     Y()
#undef X
                                   ) )
                continue;
#define X(k,r...) stats_set_wrapper(stats, key,#k, k)
            Y();
#undef X

        }
    }
    if ( NULL != line_buf )
        free( line_buf );
out:
    if ( NULL != file )
        pclose( file );
}

static void collect_panfs( struct stats_type *type ) {
    const char *me_path = "/proc/mounts";
    FILE *me_file = NULL;

    me_file = setmntent( me_path, "r" );
    if ( me_file == NULL ) {
        ERROR( "cannot open `%s': %m\n", me_path );
        goto out;
    }

    struct mntent me;
    char me_buf[4096];
    /*
       Get "slab" (kernel cache) size used by the Panasas file system.
       All mounted PanFSs will report the same slab_size value.
     */
    unsigned long long  slab_size = collect_slab_size() ;
    while ( getmntent_r( me_file, &me, me_buf, sizeof( me_buf ) ) != NULL ) {
        if ( !strcmp( me.mnt_type, "panfs" ) )
            collect_panfs_stats( type, me.mnt_dir,  slab_size );
    }

out:
    if ( me_file != NULL )
        endmntent( me_file );
}

struct stats_type panfs_stats_type = {
    .st_name = "panfs",
    .st_collect = &collect_panfs,
#define X SCHEMA_DEF
    .st_schema_def = JOIN( KEYS ),
#undef X
};
