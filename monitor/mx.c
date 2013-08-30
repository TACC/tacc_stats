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

/*
   Support for the Myricom Myrinet Express (MX) interconnect

   The code is similar to "tools/mx_counters.c" in the MX software
   package (available at ftp://ftp.myri.com/pub/MX)

   The meanings of the counters can be found at 
   http://www.myricom.com/serve/cache/642.html
*/
#include <ctype.h>
#include "myriexpress.h"
#include "mx_internals/mx__driver_interface.h"
#include "mx_internals/mx__fops.h"

#define KEYS  \
    X(Bad_CRC32__Port_0_,"E",""),\
    X(Bad_CRC32__Port_1_,"E",""),\
    X(Bad_CRC8__Port_0_,"E",""),\
    X(Bad_CRC8__Port_1_,"E",""),\
    X(Connect_source_unknown,"E",""),\
    X(Etherrx_overrun,"E",""),\
    X(Etherrx_oversized,"E",""),\
    X(Event_Queue_full,"E",""),\
    X(Fragmented_request,"E",""),\
    X(Hardware_flow_control__Port_0_,"E",""),\
    X(Hardware_flow_control__Port_1_,"E",""),\
    X(Hostname_Query_source_unknown,"E",""),\
    X(Hostname_Reply_bad_magic,"E",""),\
    X(Hostname_Reply_source_unknown,"E",""),\
    X(Interrupts_Legacy,"E",""),\
    X(Interrupts_MSI,"E",""),\
    X(Interrupts_Soft,"E",""),\
    X(Invalid_destination_peer_index,"E",""),\
    X(Nack_bad_RDMA_window,"E",""),\
    X(Nack_bad_endpoint,"E",""),\
    X(Nack_bad_session,"E",""),\
    X(Nack_bad_type,"E",""),\
    X(Nack_dest_unknown,"E",""),\
    X(Nack_endpoint_closed,"E",""),\
    X(Nack_lib_obsolete,"E",""),\
    X(Nack_mcp_obsolete,"E",""),\
    X(Nack_src_unknown,"E",""),\
    X(Net_bad_endpoint,"E",""),\
    X(Net_bad_session,"E",""),\
    X(Net_endpoint_closed,"E",""),\
    X(Net_overflow_drop,"E",""),\
    X(Net_source_unknown,"E",""),\
    X(Notify_obsolete,"E",""),\
    X(Notify_race,"E",""),\
    X(Out_of_net_slabs,"E",""),\
    X(Out_of_push_handles,"E",""),\
    X(Out_of_send_handles,"E",""),\
    X(Packet_loss__Devel___,"E",""),\
    X(Packet_misrouted,"E",""),\
    X(Packet_obsolete_unknown,"E",""),\
    X(Pull_bad_local_window,"E",""),\
    X(Pull_bad_remote_window,"E",""),\
    X(Pull_reply_bad_handle,"E",""),\
    X(Pull_reply_bad_magic,"E",""),\
    X(Pull_reply_duplicate,"E",""),\
    X(Pull_reply_obsolete,"E",""),\
    X(Pull_resend_request,"E",""),\
    X(Raw_disabled,"E",""),\
    X(Raw_overrun,"E",""),\
    X(Raw_oversized,"E",""),\
    X(Route_Table_update,"E",""),\
    X(Route_dispersion,"E",""),\
    X(Spurious_user_request,"E",""),\
    X(Unstripped_route__Port_0_,"E",""),\
    X(Unstripped_route__Port_1_,"E",""),\
    X(User_request_type_unknown,"E",""),\
    X(WDMA_slab_recycling,"E",""),\
    X(WDMA_slab_starvation,"E",""),\
    X(Wake_endpoint_closed,"E",""),\
    X(Wake_interrupt,"E",""),\
    X(Wake_race,"E",""),\
    X(buffer_drop__Port_0_,"E",""),\
    X(buffer_drop__Port_1_,"E",""),\
    X(memory_drop__Port_0_,"E",""),\
    X(memory_drop__Port_1_,"E",""),\
    X(pkt_desc_invalid__Port_0_,"E",""),\
    X(pkt_desc_invalid__Port_1_,"E",""),\
    X(recv_pkt_errors__Port_0_,"E",""),\
    X(recv_pkt_errors__Port_1_,"E",""),\
    X(rx_Connect,"E",""),\
    X(rx_Ethernet_Big,"E",""),\
    X(rx_Ethernet_Small,"E",""),\
    X(rx_Hostname_Query,"E",""),\
    X(rx_Hostname_Reply,"E",""),\
    X(rx_KBytes__Port_0_,"E,U=KB",""),\
    X(rx_KBytes__Port_1_,"E,U=KB",""),\
    X(rx_Large_Rndv,"E",""),\
    X(rx_Medium,"E",""),\
    X(rx_Nack_Lib,"E",""),\
    X(rx_Nack_MCP,"E",""),\
    X(rx_Notify,"E",""),\
    X(rx_Probe_Nack,"E",""),\
    X(rx_Pull_Reply,"E",""),\
    X(rx_Pull_Request,"E",""),\
    X(rx_Raw,"E",""),\
    X(rx_Small,"E",""),\
    X(rx_Tiny,"E",""),\
    X(rx_Truc,"E",""),\
    X(tx_Connect,"E",""),\
    X(tx_Ether_Myri_Multicast,"E",""),\
    X(tx_Ether_Myri_Unicast,"E",""),\
    X(tx_Hostname_Query,"E",""),\
    X(tx_Hostname_Reply,"E",""),\
    X(tx_KBytes__Port_0_,"E,U=KB",""),\
    X(tx_KBytes__Port_1_,"E,U=KB",""),\
    X(tx_Large_Rndv,"E",""),\
    X(tx_Medium,"E",""),\
    X(tx_Nack_Lib,"E",""),\
    X(tx_Nack_MCP,"E",""),\
    X(tx_Notify,"E",""),\
    X(tx_Probe,"E",""),\
    X(tx_Probe_Ack,"E",""),\
    X(tx_Probe_Nack,"E",""),\
    X(tx_Pull_Reply,"E",""),\
    X(tx_Pull_Request,"E",""),\
    X(tx_Raw,"E",""),\
    X(tx_Small,"E",""),\
    X(tx_Tiny,"E",""),\
    X(tx_Truc,"E",""),\
    X(tx_queued,"E","")

static void get_new_mx_counter_label(  char *label ) {
    /*
       Replace "Net send" in the original counter label
       with "tx", "Net recv" with "rx", and all non-alphanumeric
       characters with "_"
     */
    int i;
    char new_label[MX_MAX_STR_LEN], *orig = label;
    *new_label = '\0';

    if ( strncasecmp( label, "net ", 4 ) ) {
basecase:
        strcat( new_label, label );
    }
    else {
        if ( !strncasecmp( label + 4, "recv", 4 ) ) {
            strcpy( new_label, "rx" );
            label += 8;
        }
        else if ( !strncasecmp( label + 4, "send", 4 ) ) {
            strcpy( new_label, "tx" );
            label += 8;
        }
        goto basecase;
    }

    for ( i = 0; i < strlen( new_label ); ++i ) {
        if ( !isalnum( new_label[i] ) ) new_label[i] = '_';
    }

    strcpy( orig, new_label );
}

static void collect_mx( struct stats_type *type ) {
    struct stats *stats = NULL;
    mx_endpt_handle_t fd;
    mx_return_t ret;
    uint32_t counters[1024];
    uint32_t board_id = 0, i;
    static uint32_t count = 0;
    static char *counter_labels = NULL;
    static int hasMX = 1, canOpenBoard = 0;

    if ( !hasMX ) return;
    mx_init();
    if ( !canOpenBoard ) {
        if ( MX_SUCCESS != mx_open_any_board( &fd ) ) {
            hasMX = 0;
            mx_finalize();
            return;
        }
        canOpenBoard = 1;
    }

    stats = get_current_stats( type, NULL );
    if ( stats == NULL )
        goto out;

    if ( !counter_labels ) {
        if ( MX_SUCCESS != ( ret = mx_get_info( NULL, MX_COUNTERS_COUNT, &board_id, sizeof ( board_id ), &count, sizeof ( count ) ) ) ) {
            ERROR( "mx_get_info failed on MX_COUNTERS_COUNT: %s\n", mx_strerror ( ret ) );
            goto out;
        }
        /* we cache the labels in "counter_labels" */
        counter_labels = ( char * )malloc ( MX_MAX_STR_LEN * count );
        if ( NULL == counter_labels )
            goto out;

        if ( MX_SUCCESS != ( ret = mx_get_info( NULL, MX_COUNTERS_LABELS, &board_id, sizeof ( board_id ), counter_labels, MX_MAX_STR_LEN * count ) ) ) {
            ERROR( "mx_get_info failed on MX_COUNTERS_LABELS: %s\n", mx_strerror ( ret ) );
            free( counter_labels );
            counter_labels = NULL;
            goto out;
        }

        for ( i = 0; i < count; ++i )
            get_new_mx_counter_label( &counter_labels[i * MX_MAX_STR_LEN] );
    }

    do {
        ret = mx_get_info( NULL, MX_COUNTERS_VALUES, &board_id, sizeof ( board_id ),
                           counters, sizeof ( counters ) );
        if ( MX_SUCCESS != ret && EBUSY != errno ) {
            ERROR( "mx_get_info failed on MX_COUNTERS_VALUES: %s\n", mx_strerror ( ret ) );
            goto out;
        }
    }
    while ( ret );

    for ( i = 0; i < count; ++i ) {
        stats_set( stats, &counter_labels[i * MX_MAX_STR_LEN], counters[i] );
    }

out:
    mx__close( fd );
    mx_finalize();
}

struct stats_type mx_stats_type = {
    .st_name = "mx",
    .st_collect = &collect_mx,
#define X SCHEMA_DEF
    .st_schema_def = JOIN( KEYS ),
#undef X
};
