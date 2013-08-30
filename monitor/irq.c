#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <unistd.h>
#include "stats.h"
#include "trace.h"
#include "string1.h"

/*
   Support for /proc/interrupts and /proc/softirqs (see
   arch/x86/kernel/irq.c and kernel/softirq.c in the Linux
   kernel source tree)

   This source file must be preprocessed by m4 !
*/

/* an m4 for-loop macro */
define( `forloop',`ifelse($#,0,``$0'',`ifelse(eval($2<$3),1,`pushdef(`$1', $2 )$4`'popdef(`$1' )$0( `$1',incr($2),$3,`$4' )')' )')

/* must have at least 1 CPU */
#define KEYS X(cpu0,"E",) \
forloop(`i', 1, NCPUS, ``, X( cpu'i`,"E",)'')

/**************************************/
static void collect_irq_stats( struct stats_type *type, const char *path ) {
    FILE *file = NULL;
    char *line = NULL;
    size_t line_size = 0;

    file = fopen( path, "r" );
    if ( file == NULL ) {
        //ERROR( "cannot open `%s': %m\n", path );
        goto out;
    }

    while ( 0 <= getline( &line, &line_size, file ) ) {
        char *rest = line;
        char *key = wsep( &rest );
        if ( key == NULL || rest == NULL )
            continue;

        if ( ! strncasecmp( key, "cpu0", 4 ) )
            continue;
#define X(k,r...) k = 0
        unsigned long long KEYS;
#undef X
        if ( 0 <    sscanf( rest,
#define X(k,r...) " %llu"
                            JOIN( KEYS )
#undef X
#define X(k,r...) &k
                            , KEYS ) ) {
#undef X
            /* remove the colon */
            char *t = key;
            do {
                if ( ':' == *t )
                    *t = '\0';
            }
            while ( *t++ );

            /* check if the key is a number of not */
            strtoul( key, &t, 10 );
            if ( '\0' == *t ) {
                /* so the key is a number, e.g. like the following
                             CPU0       CPU1       CPU2       CPU3
                	0:        198          1          0          0   IO-APIC-edge      timer
                	1:          0          2          2          3   IO-APIC-edge      i8042
                	4:          0          0          4          0   IO-APIC-edge      serial
                	6:          0          0          1          1   IO-APIC-edge      floppy
                	8:          0          0          1          0   IO-APIC-edge      rtc0
                	...
                */
                /* get the real device name from the last column(s) */
                /* An x86 IRQ description is of form "%s-%s %s" where the first
                   %s is from the "name" field, e.g. in arch/x86/kernel/apic/io_apic.c :

                   static struct irq_chip ioapic_chip __read_mostly = {
                           .name                   = "IO-APIC",
                           .irq_startup            = startup_ioapic_irq,
                           .irq_mask               = mask_ioapic_irq,
                           .irq_unmask             = unmask_ioapic_irq,
                           .irq_ack                = ack_apic_edge,
                           .irq_eoi                = ack_apic_level,
                   #ifdef CONFIG_SMP
                           .irq_set_affinity       = ioapic_set_affinity,
                   #endif
                           .irq_retrigger          = ioapic_retrigger_irq,
                   };
                */
                /* ignore interrupts from certain devices, e.g. keyboard, floppy, USB, etc */
                if ( strstr( rest, " i8042" ) || strstr( rest, " floppy" ) || strstr( rest, ":usb" ) || strstr( rest, " serial" ) ) continue;
                size_t s = strspn( rest, "0123456789: \t\n\r" );
                if ( '\0' == rest[s] ) continue; /* there is no last column; move on */
                rest += s;
                wsep( &rest );
                if ( NULL == rest ) continue;
                s = strspn( rest, " \t\n\r" );
                if ( '\0' == rest[s] ) continue;
                /* replace every space with underscore */
                t = key = rest + s;
                do {
                    if ( '\r' == *t || '\n' == *t ) *t = '\0';
                    if ( isspace( *t ) ) *t = '_';
                }
                while ( *t++ );
            }

            struct stats *stats = get_current_stats( type, key );
            if ( NULL ==  stats ) break;
#define X(k,r...) stats_set(stats, #k, k)
            KEYS;
#undef X
        }
    }

out:
    if ( NULL != line )
        free( line );
    if ( NULL != file )
        fclose( file );

}

/**************************************/
static void collect_irq( struct stats_type *type ) {
    collect_irq_stats( type, "/proc/interrupts" );
    collect_irq_stats( type, "/proc/softirqs" );
}

struct stats_type irq_stats_type = {
    .st_name = "irq",
    .st_collect = &collect_irq,
#define X SCHEMA_DEF
    .st_schema_def = JOIN( KEYS ),
#undef X
};
