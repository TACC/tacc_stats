#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <errno.h>
#include <malloc.h>
#include <ctype.h>
#include <fcntl.h>
#include "stats.h"
#include "trace.h"

// $ ls -l /dev/cpu/0
// total 0
// crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
// crw-------  1 root root 202, 0 Oct 28 18:47 msr

#define MSR(name,number) static const uint64_t name=number;

// Pentium 4/Netburst performance counters
MSR( BPU_COUNTER0 , 0x300 ) // branch-prediction unit related counters
MSR( BPU_COUNTER1 , 0x301 )
MSR( BPU_COUNTER2 , 0x302 )
MSR( BPU_COUNTER3 , 0x303 )
MSR( FLAME_COUNTER0 , 0x308 )
MSR( FLAME_COUNTER1 , 0x309 )
MSR( FLAME_COUNTER2 , 0x30A )
MSR( FLAME_COUNTER3 , 0x30B )
MSR( IQ_COUNTER0 , 0x30C ) // instruction queue-related counters
MSR( IQ_COUNTER1 , 0x30D )
MSR( IQ_COUNTER2 , 0x30E )
MSR( IQ_COUNTER3 , 0x30F )
MSR( IQ_COUNTER4 , 0x310 )
MSR( IQ_COUNTER5 , 0x311 )
MSR( MS_COUNTER0 , 0x304 ) // microinstruction sequencer-related counters
MSR( MS_COUNTER1 , 0x305 )
MSR( MS_COUNTER2 , 0x306 )
MSR( MS_COUNTER3 , 0x307 )

// Pentium 4/Netburst CCCRs (Counter Configuration Control Registers)
MSR( BPU_CCCR0 , 0x360 )
MSR( BPU_CCCR1 , 0x361 )
MSR( BPU_CCCR2 , 0x362 )
MSR( BPU_CCCR3 , 0x363 )
MSR( FLAME_CCCR0 , 0x368 )
MSR( FLAME_CCCR1 , 0x369 )
MSR( FLAME_CCCR2 , 0x36A )
MSR( FLAME_CCCR3 , 0x36B )
MSR( IQ_CCCR0 , 0x36C )
MSR( IQ_CCCR1 , 0x36D )
MSR( IQ_CCCR2 , 0x36E )
MSR( IQ_CCCR3 , 0x36F )
MSR( IQ_CCCR4 , 0x370 )
MSR( IQ_CCCR5 , 0x371 )
MSR( MS_CCCR0 , 0x364 )
MSR( MS_CCCR1 , 0x365 )
MSR( MS_CCCR2 , 0x366 )
MSR( MS_CCCR3 , 0x367 )

// Pentium 4/Netburst ESCRs (Event Selection Control Registers)
// The full names of these abbreviated names can be found
// by searching Intel patents.
MSR( ALF_ESCR0      , 0x3CA ) // allocation and freelist manager
MSR( ALF_ESCR1      , 0x3CB )
MSR( BPU_ESCR0      , 0x3B2 ) // branch prediction unit
MSR( BPU_ESCR1      , 0x3B3 )
MSR( BSU_ESCR0      , 0x3A0 ) // bus sequencing unit
MSR( BSU_ESCR1      , 0x3A1 )
MSR( CRU_ESCR0      , 0x3B8 ) // checker retirement unit
MSR( CRU_ESCR1      , 0x3B9 )
MSR( CRU_ESCR2      , 0x3CC )
MSR( CRU_ESCR3      , 0x3CD )
MSR( CRU_ESCR4      , 0x3E0 )
MSR( CRU_ESCR5      , 0x3E1 )
MSR( DAC_ESCR0      , 0x3A8 ) // data-cache address control (data access control)
MSR( DAC_ESCR1      , 0x3A9 )
MSR( FIRM_ESCR0     , 0x3A4 )
MSR( FIRM_ESCR1     , 0x3A5 )
MSR( FLAME_ESCR0    , 0x3A6 )
MSR( FLAME_ESCR1    , 0x3A7 )
MSR( FSB_ESCR0      , 0x3A2 ) // front side bus
MSR( FSB_ESCR1      , 0x3A3 )
MSR( IQ_ESCR0       , 0x3BA ) // instruction queue
MSR( IQ_ESCR1       , 0x3BB )
MSR( IS_ESCR0       , 0x3B4 ) // instruction sequencer
MSR( IS_ESCR1       , 0x3B5 )
MSR( ITLB_ESCR0     , 0x3B6 ) // instruction translation lookaside buffer
MSR( ITLB_ESCR1     , 0x3B7 )
MSR( IX_ESCR0       , 0x3C8 ) // instruction translation
MSR( IX_ESCR1       , 0x3C9 )
MSR( MOB_ESCR0      , 0x3AA ) // memory ordering buffer
MSR( MOB_ESCR1      , 0x3AB )
MSR( MS_ESCR0       , 0x3C0 ) // microinstruction sequencer
MSR( MS_ESCR1       , 0x3C1 )
MSR( PMH_ESCR0      , 0x3AC ) // page miss handler
MSR( PMH_ESCR1      , 0x3AD )
MSR( PM_ESCR0       , 0x3AC )
MSR( RAT_ESCR0      , 0x3BC ) // register alias table
MSR( RAT_ESCR1      , 0x3BD )
MSR( SAAT_ESCR0     , 0x3AE ) // segmentation and address translation
MSR( SAAT_ESCR1     , 0x3AF )
MSR( SSU_ESCR0      , 0x3BE ) // scheduler and scorebord unit
MSR( TBPU_ESCR0     , 0x3C2 ) // trace branch prediction unit
MSR( TBPU_ESCR1     , 0x3C3 )
MSR( TC_ESCR0       , 0x3C4 ) // trace cache
MSR( TC_ESCR1       , 0x3C5 )
MSR( U2L_ESCR0      , 0x3B0 )
MSR( U2L_ESCR1      , 0x3B1 )

/* the first 6 are for L2 cache hit/miss counting,
   the rest are for retired SSE/floating-point instruction counting
 */
#define KEYS \
    X( BPU_COUNTER0 , "E,W=40", ""), \
    X( BPU_COUNTER2 , "E,W=40", ""), \
    X( BPU_CCCR0 , "C", ""), \
    X( BPU_CCCR2 , "C", ""), \
    X( BSU_ESCR0 , "C", ""), \
    X( BSU_ESCR1 , "C", ""), \
    X( IQ_COUNTER2 , "E,W=40", ""), \
    X( FIRM_ESCR0 , "C", ""), \
    X( FIRM_ESCR1 , "C", ""), \
    X( FLAME_CCCR0 , "C", ""), \
    X( FLAME_CCCR2 , "C", ""), \
    X( CRU_ESCR3 , "C", ""), \
    X( IQ_CCCR2 , "C", "")

static int cpu_is_netburst( unsigned cpu ) {
    char cpuid_path[80];
    int cpuid_fd = -1;
    uint32_t buf[4];
    int rc = 0;

    /* Open /dev/cpuid/cpu/cpuid. */
    snprintf( cpuid_path, sizeof( cpuid_path ), "/dev/cpu/%d/cpuid", cpu );
    cpuid_fd = open( cpuid_path, O_RDONLY );
    if ( cpuid_fd < 0 ) {
        ERROR( "cannot open `%s': %m\n", cpuid_path );
        goto out;
    }

    /* Get cpu vendor. */
    if ( pread( cpuid_fd, buf, sizeof( buf ), 0x0 ) < 0 ) {
        ERROR( "cannot read cpu vendor through `%s': %m\n", cpuid_path );
        goto out;
    }

    buf[0] = buf[2], buf[2] = buf[3], buf[3] = buf[0];
    TRACE( "cpu %d, vendor `%.12s'\n", cpu, ( char* ) buf + 4 );

    if ( strncmp( ( char* ) buf + 4, "GenuineIntel", 12 ) != 0 )
        goto out;

    if ( pread( cpuid_fd, buf, sizeof( buf ), 1 ) < 0 ) {
        ERROR( "cannot read `%s': %m\n", cpuid_path );
        goto out;
    }

    TRACE( "cpu %d, buf %08x %08x %08x %08x\n", cpu, buf[0], buf[1], buf[2], buf[3] );

    unsigned base_family = ( buf[0] >> 8 ) & 0xF;
    /* family 15 is the Pentium 4/Netburst */
    rc = ( 15 == base_family );
out:
    if ( cpuid_fd >= 0 )
        close( cpuid_fd );

    return rc;
}

static int begin_pmc_cpu( unsigned cpu, uint64_t events[][4], size_t nr_events ) {
    int rc = -1;
    char msr_path[80];
    int msr_fd = -1;

    snprintf( msr_path, sizeof( msr_path ), "/dev/cpu/%d/msr", cpu );
    msr_fd = open( msr_path, O_RDWR );
    if ( msr_fd < 0 ) {
        ERROR( "cannot open `%s': %m\n", msr_path );
        goto out;
    }

    /* set up the ESCR and CCCRs */
    int i;
    for ( i = 0; i < nr_events; ++i ) {
        TRACE( "CCCR[%08lX]=%08lX, ESCR[%08lX]=%08lX\n", events[i][2], events[i][3] , events[i][0] , events[i][1] );
        if ( pwrite( msr_fd, &events[i][3], sizeof( events[i][3] ), events[i][2] ) < 0 ) {
            ERROR( "cannot write to CCCR[%08lX] through `%s': %m\n",
                   events[i][2],
                   msr_path );
            goto out;
        }
        if ( pwrite( msr_fd, &events[i][1], sizeof( events[i][1] ), events[i][0] ) < 0 ) {
            ERROR( "cannot write to ESCR[%08lX] through `%s': %m\n",
                   events[i][0],
                   msr_path );
            goto out;
        }
    }
    rc = 0;
out:
    if ( msr_fd >= 0 )
        close( msr_fd );

    return rc;
}

//
// Pentium 4/Netburst performance counters are quite complex
// to set up. In the simplest case, one needs to configure
// one ESCR and one CCCR to count one type of event, e.g. L2 cache
// miss. In more involved cases, one needs to set up "upstream"
// counters and "downstream" counters and do the actual counting
// in the downstream. For example, upstream counters could
// count SSE instructions (including those which are speculatively
// executed), and the downstream counterparts count those that are
// actually *retired*.
//

#define ESCR_SETUP(event_select, event_mask, tag_value, tag_enable) \
    ( ((event_select&63ULL) << 25) \
      | ((event_mask&65535ULL) << 9) \
      | ((tag_value&15ULL) << 5) \
      | ((tag_enable&1ULL) << 4) \
      | (1ULL << 3)  /* Count in OS mode (CPL > 0). */ \
      | (1ULL << 2)  /* Count in user mode (CPL == 0). */ \
    )

#define CCCR_SETUP(cccr_select) \
    ( ((cccr_select&7ULL) << 13) \
      | (3ULL << 16)  /* Must be set to 3 */ \
      | (1ULL << 12)  /* Enable */ \
    )

/* RD_2ndL = Read 2nd level cache */
/* 0xC : BSQ_cache_reference, BSQ=Bus Sequence Queue */
#define RD_2ndL_MISS_ESCR ESCR_SETUP(0xC,(1<<8),0,0)
#define RD_2ndL_MISS_CCCR CCCR_SETUP(7)
/* 7 = (1<<0)|(1<<1)|(1<<2) = HITS | HITE | HITM
   S = Shared, E = Exclusive, M = Modified */
#define RD_2ndL_HIT_ESCR  ESCR_SETUP(0xC,7,0,0)
#define RD_2ndL_HIT_CCCR  CCCR_SETUP(7)

/* Floating-point instruction counting (upstream)
   DP = Double precision SSE
   SP = Single precision SSE
 */
#define Packed_DP_uop_ESCR ESCR_SETUP(0xC,(1<<15),1,1)
#define Packed_DP_uop_CCCR CCCR_SETUP(1)
#define Packed_SP_uop_ESCR ESCR_SETUP(0x8,(1<<15),1,1)
#define Packed_SP_uop_CCCR CCCR_SETUP(1)
#define Scalar_DP_uop_ESCR ESCR_SETUP(0xE,(1<<15),1,1)
#define Scalar_DP_uop_CCCR CCCR_SETUP(1)
#define Scalar_SP_uop_ESCR ESCR_SETUP(0xA,(1<<15),1,1)
#define Scalar_SP_uop_CCCR CCCR_SETUP(1)
#define x87_FP_uop_ESCR    ESCR_SETUP(0x4,(1<<15),1,1)
#define x87_FP_uop_CCCR    CCCR_SETUP(1)
/* *Retired* floating-point instruction counting (downstream) */
#define Execution_event_ESCR ESCR_SETUP(0xC,1,0,0)
#define Execution_event_CCCR CCCR_SETUP(5)

static int begin_pmc( struct stats_type *type ) {
    int nr = 0;
    uint64_t events[][4] = {
        {
            BSU_ESCR0, RD_2ndL_MISS_ESCR,
            BPU_CCCR0, RD_2ndL_MISS_CCCR
        },
        {
            BSU_ESCR1, RD_2ndL_HIT_ESCR,
            BPU_CCCR2, RD_2ndL_HIT_CCCR
        },
        {
            FIRM_ESCR0, Scalar_DP_uop_ESCR,
            FLAME_CCCR0, Scalar_DP_uop_CCCR
        },
        {
            FIRM_ESCR1, Packed_DP_uop_ESCR,
            FLAME_CCCR2, Packed_DP_uop_CCCR
        },
        {
            CRU_ESCR3, Execution_event_ESCR,
            IQ_CCCR2, Execution_event_CCCR
        }
    };

    int i;
    for ( i = 0; i < nr_cpus; i++ ) {
        if ( cpu_is_netburst( i ) )
            if ( begin_pmc_cpu( i, events, sizeof( events ) / sizeof( events[0] ) ) == 0 )
                nr++;
    }

    return nr > 0 ? 0 : -1;
}

static void collect_pmc_cpu( struct stats_type *type, unsigned cpu ) {
    struct stats *stats = NULL;
    char msr_path[80];
    int msr_fd = -1;

    char cpu_s[80];
    sprintf( cpu_s, "%d", cpu );
    stats = get_current_stats( type, cpu_s );
    if ( stats == NULL )
        goto out;

    TRACE( "cpu %s\n", cpu_s );

    snprintf( msr_path, sizeof( msr_path ), "/dev/cpu/%s/msr", cpu_s );
    msr_fd = open( msr_path, O_RDONLY );
    if ( msr_fd < 0 ) {
        ERROR( "cannot open `%s': %m\n", msr_path );
        goto out;
    }

#define X(k,r...) \
    ({ \
        uint64_t val = 0; \
        if (pread(msr_fd, &val, sizeof(val), k) < 0) \
            ERROR("cannot read `%s' (%08lX) through `%s': %m\n", #k, k, msr_path); \
        else \
            stats_set(stats, #k, val); \
    })
    KEYS;
#undef X

out:
    if ( msr_fd >= 0 )
        close( msr_fd );
}

static void collect_pmc( struct stats_type *type ) {
    int i;
    for ( i = 0; i < nr_cpus; i++ ) {
        if ( cpu_is_netburst( i ) )
            collect_pmc_cpu( type, i );
    }
}

struct stats_type intel_p4_stats_type = {
    .st_name = "intel_p4",
    .st_begin = &begin_pmc,
    .st_collect = &collect_pmc,
#define X SCHEMA_DEF
    .st_schema_def = JOIN( KEYS ),
#undef X
};
