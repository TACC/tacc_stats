#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <unistd.h>
#include "stats.h"
#include "trace.h"
#include "string1.h"

/*
   Support for NFS (client) version 3.

   There are many utilities to get NFS stats, e.g. iostat, nfsiostat, nfsstat, mountstats.
   We will imitate the last one, which is a Python script in "nfs-utils" package, available
   at http://nfs.sf.net

   There are two parts of NFS stats: NFS and RPC (Remote Procedure Calls, an inter-process
   communication protocol on which NFS is implemented.)

   For NFS stats, please refer to include/linux/nfs_iostat.h in the Linux kernel source tree.
   For RPC stats, refer to include/linux/sunrpc/metrics.h and net/sunrpc/stats.c in the Linux kernel source tree.
*/

#define NFS_BYTES \
    X(normal_read, "E,U=B", ""), \
    X(normal_write, "E,U=B", ""), \
    X(direct_read, "E,U=B", ""), \
    X(direct_write, "E,U=B", ""), \
    X(server_read, "E,U=B", ""), \
    X(server_write, "E,U=B", ""), \
    X(read_page, "E", ""), \
    X(write_page, "E", "")

#define NFS_EVENTS \
    X(inode_revalidate, "E", ""), \
    X(dentry_revalidate, "E", ""), \
    X(data_invalidate, "E", ""), \
    X(attr_invalidate, "E", ""), \
    X(vfs_open, "E", ""), \
    X(vfs_lookup, "E", ""), \
    X(vfs_access, "E", ""), \
    X(vfs_updatepage, "E", ""), \
    X(vfs_readpage, "E", ""), \
    X(vfs_readpages, "E", ""), \
    X(vfs_writepage, "E", ""), \
    X(vfs_writepages, "E", ""), \
    X(vfs_getdents, "E", ""), \
    X(vfs_setattr, "E", ""), \
    X(vfs_flush, "E", ""), \
    X(vfs_fsync, "E", ""), \
    X(vfs_lock, "E", ""), \
    X(vfs_release, "E", ""), \
    X(congestion_wait, "E", ""), \
    X(setattr_trunc, "E", ""), \
    X(extend_write, "E", ""), \
    X(silly_rename, "E", ""), \
    X(short_read, "E", ""), \
    X(short_write, "E", ""), \
    X(delay, "E", "")

/*
   For RPC_STATS, see xprt_rdma_print_stats() (net/sunrpc/xprtrdma/transport.c)
   xs_tcp_print_stats(), and xs_udp_print_stats() (net/sunrpc/xprtsock.c)
   and include/linux/sunrpc/xprt.h in the Linux kernel source tree.
*/

#define RPC_STATS \
    X(rpc_send, "E", ""), \
    X(rpc_recv, "E", ""), \
    X(rpc_bad_xid, "E", ""), \
    X(rpc_req_u, "E", ""), \
    X(rpc_bklog_u, "E", "")

/*
   For RPC op stats, see include/linux/sunrpc/metrics.h
   in the Linux kernel source tree.
*/

#define RPC_OPS Y(access),Y(commit),Y(create),Y(fsinfo),Y(fsstat),Y(getattr),Y(link),Y(lookup),Y(mkdir),Y(mknod),Y(pathconf),Y(read),Y(readdir),Y(readdirplus),Y(readlink),Y(remove),Y(rename),Y(rmdir),Y(setattr),Y(symlink),Y(write)
#define Y(x) \
    X(rpc_##x##_op, "E", ""), \
    X(rpc_##x##_trans, "E", ""), \
    X(rpc_##x##_timeout, "E", ""), \
    X(rpc_##x##_send, "E,U=B", ""), \
    X(rpc_##x##_recv, "E,U=B", ""), \
    X(rpc_##x##_queue, "E,U=ms", ""), \
    X(rpc_##x##_rtt, "E,U=ms", ""), \
    X(rpc_##x##_exec, "E,U=ms", "")

/* list of metrics we are interested */
#define KEYS NFS_BYTES,NFS_EVENTS,RPC_STATS,RPC_OPS,X(kernel_slab_size, "U=MB", "")

// $ cat /proc/self/mountstats
// device ifs10G.blah.blah.blah.com:/ifs mounted on /ifs with fstype nfs statvers=1.0
//        opts:   rw,vers=3,rsize=32768,wsize=32768,namlen=255,acregmin=3,acregmax=60,acdirmin=30,acdirmax=60,hard,proto=tcp,timeo=600,retrans=2,sec=sys,mountaddr=10.113.10.26,mountvers=3,mountport=1021,mountproto=tcp,local_lock=none
//        age:    1309110
//        caps:   caps=0x3fc7,wtmult=8192,dtsize=32768,bsize=0,namlen=255
//        sec:    flavor=1,pseudoflavor=1
//        events: 86104644 8232551112 1009346 29773140 77713963 3396235 8710920811 217953089 535540 4419865 165269865 3054740392 13240410 948750 3214807 3239326 34443 71334984 0 85000 197520825 4502 0 0 0
//        bytes:  4886067767364 671548484867 0 0 1268384471881 672425463273 313433034 165269865
//        RPC iostats version: 1.0  p/v: 100003/3 (nfs)
//        xprt:   tcp 766 1 1 0 0 172670997 172670964 33 3451662215 293843845166
//        per-op statistics
//       NULL: 0 0 0 0 0 0 0 0
//    GETATTR: 86102054 86103087 0 13515430340 9643670764 5776193 34879595 42411140
//    SETATTR: 1410718 1410720 0 283592512 203143968 20769 1031591 1074107
//     LOOKUP: 4948338 4948368 0 870100516 855181240 234293 4414050 4731815
//     ACCESS: 9885966 9886246 0 1553191308 1186340728 603376 5228075 6007612
//   READLINK: 12965 12965 0 2331180 1904228 78 2065 2360
//       READ: 40661028 40661029 0 6667603140 1273590220520 53470812 194367680 249334714
//      WRITE: 22095837 22095838 0 676314934552 3534070784 212745097913 103711782 212850213433
//     CREATE: 1253732 1253734 0 265311588 340412760 59116 3604753 3687164
//      MKDIR: 51433 51433 0 10721240 13948664 1603 159584 162099
//    SYMLINK: 8125 8125 0 1968044 2204880 751 34759 35680
//      MKNOD: 0 0 0 0 0 0 0 0
//    ......
//

/**************************************/
static void collect_nfs_bytes( struct stats_type *type, const char *d_name, const char *rest ) {
#define X(k,r...) k = 0
    unsigned long long NFS_BYTES;
#undef X
    if ( NULL == rest || NULL == d_name ) return;

    struct stats *nfs_stats = get_current_stats( type, d_name );
    if ( NULL ==  nfs_stats ) return;
    sscanf( rest,
#define X(k,r...) "%llu "
            JOIN( NFS_BYTES )
#undef X
#define X(k,r...) &k
            , NFS_BYTES );
#undef X
#define X(k,r...) stats_set(nfs_stats, #k, k)
    NFS_BYTES;
#undef X
}
/**************************************/
static void collect_nfs_events( struct stats_type *type,  const char *d_name, const char *rest ) {
#define X(k,r...) k = 0
    unsigned long long NFS_EVENTS;
#undef X
    if (  NULL == rest || NULL == d_name ) return;

    struct stats *nfs_stats = get_current_stats( type, d_name );
    if ( NULL ==  nfs_stats ) return;
    sscanf( rest,
#define X(k,r...) "%llu "
            JOIN( NFS_EVENTS )
#undef X
#define X(k,r...) &k
            , NFS_EVENTS );
#undef X
#define X(k,r...) stats_set(nfs_stats, #k, k)
    NFS_EVENTS;
#undef X
}

/**************************************/
static void collect_rpc_stats( struct stats_type *type,  const char *d_name, const char *rest ) {
#define X(k,r...) k = 0
    unsigned long long RPC_STATS;
#undef X
    char *skiplist, *fmt;
    if (  NULL == rest || NULL == d_name ) return;

    struct stats *nfs_stats = get_current_stats( type, d_name );
    if ( NULL ==  nfs_stats ) return;
    if ( !strncasecmp( rest, "tcp", 3 ) || !strncasecmp( rest, "rdma", 4 ) ) {
        /* skip the first 6 fields */
        skiplist = "%*s %*s %*s %*s %*s %*s";
    }
    else if  ( !strncasecmp( rest, "udp", 3 ) ) {
        /* skip the first 3 fields */
        skiplist = "%*s %*s %*s ";
    }
    else  {
        /* cannot recognize the network protocol */
        return;
    }
    fmt = NULL;
#define X(k,r...) "%llu "
    asprintf( &fmt, "%s %s ", skiplist, JOIN( RPC_STATS ) );
#undef X

    if ( NULL == fmt ) return;
#define X(k,r...) &k
    sscanf( rest, fmt, RPC_STATS );
#undef X
    free( fmt );
#define X(k,r...) stats_set(nfs_stats, #k, k)
    RPC_STATS;
#undef X
}
/**************************************/
static void stats_set_wrapper( struct stats *nfs_stats, const char *key1, const char *key2, unsigned long long val ) {
    /*  If key1 is like "write" and key2 is like "rpc__op",
        merge the two keys into "rpc_write_op".

        This is a helper function used by collect_rpc_ops
     */
    char s[1024];
    char *t = strstr( key2, "__" );
    if ( NULL == t ) return;
    strcpy( s, key2 );
    s[t - key2 + 1] = '\0';
    strcat( s, key1 );
    strcat( s, t + 1 );
    /*  insert the metric value using the new key */
    stats_set( nfs_stats, s, val );
}

static void collect_rpc_ops( struct stats_type *type, const char *d_name, const char *key, const char *rest ) {
    char *t;
    int i;
#define X(k,r...) k = 0
    unsigned long long Y();
#undef X
    if ( NULL == key || NULL == rest || NULL == d_name ) return;

    struct stats *nfs_stats = get_current_stats( type, d_name );
    if ( NULL ==  nfs_stats ) return;
    sscanf( rest,
#define X(k,r...) "%llu "
            JOIN( Y() )
#undef X
#define X(k,r...) &k
            , Y() );
#undef X
    /* if 'key' is something like "WRITE:"
       create a string "write"
     */
    t = strdupa( key );
    if ( NULL == t ) return;
    for ( i = 0; i < strlen( t ); ++i ) {
        if ( ':' == t[i] ) {
            t[i] = '\0';
            break;
        }
        t[i] = tolower( t[i] );
    }

#define X(k,r...) stats_set_wrapper(nfs_stats, t,#k, k)
    Y();
#undef X
}

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
        if ( strncasecmp( line, "nfs_", 4 ) )
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

/**************************************/
static void collect_nfs( struct stats_type *type ) {

    const char *path = "/proc/self/mountstats";
    FILE *file = NULL;
    char *line = NULL, *d_name;
    size_t line_size = 0;
    unsigned long long slab_size;

    /*
       Get "slab" (kernel cache) size used by NFS.
       All mounted NFSs will report the same slab_size value.
     */
    slab_size = collect_slab_size();

    file = fopen( path, "r" );
    if ( file == NULL ) {
        ERROR( "cannot open `%s': %m\n", path );
        goto out;
    }

    while ( 0 <= getline( &line, &line_size, file ) ) {
        char *key, *rest = line;

        key = wsep( &rest );
        if ( key == NULL || rest == NULL )
            continue;

        if ( strncmp( key, "device", 6 ) )
            continue;

nextDevice:
        if ( NULL == strstr( rest, "with fstype nfs" ) )
            continue;

        if ( NULL == ( key = strstr( rest, "mounted on" ) ) )
            continue;

        rest = key + sizeof( "mounted on" );
        d_name = wsep( &rest );
        if ( d_name ) {
            struct stats *stats = get_current_stats( type, d_name );
            if ( stats )
                stats_set( stats, "kernel_slab_size", slab_size );

            /* here begins the NFS stats */
            /* first, make a copy of d_name, since d_name is just a pointer
               into "line", which will be overwritten */
            d_name = strdupa( d_name );
            int rpcstats = 0;
            while ( getline( &line, &line_size, file ) >= 0 ) {
                rest  = line;
                key = wsep( &rest );
                if ( NULL == key || NULL == rest )
                    continue;
                if ( !strncmp( key, "device", 6 ) ) /* done with this device ? */
                    goto nextDevice;
                if ( !strncasecmp( key, "per-op", 6 ) && !strncasecmp( rest, "stat", 4 ) ) {
                    /* here begins the per-op RPC stats */
                    rpcstats = 1;
                    continue;
                }
                if ( !rpcstats ) {
                    if	( !strncasecmp( key, "events:", 7 ) )
                        collect_nfs_events( type, d_name, rest );
                    else if ( !strncasecmp( key, "bytes:", 6 ) )
                        collect_nfs_bytes( type, d_name, rest );
                    else if ( !strncasecmp( key, "xprt:", 5 ) )
                        collect_rpc_stats( type, d_name, rest );
                }
                else {
                    collect_rpc_ops( type, d_name, key, rest );
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

struct stats_type nfs_stats_type = {
    .st_name = "nfs",
    .st_collect = &collect_nfs,
#define X SCHEMA_DEF
    .st_schema_def = JOIN( KEYS ),
#undef X
};
