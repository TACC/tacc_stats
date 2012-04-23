#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <getopt.h>
#include <signal.h>
#include <malloc.h>
#include <errno.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include "string1.h"
#include "stats.h"
#include "stats_file.h"
#include "trace.h"
#include "pscanf.h"
#include <dirent.h>
#include <ctype.h>

time_t current_time;
char current_jobid[10240] = "0";
int nr_cpus;

static void alarm_handler( int sig ) {
}

static int open_lock_timeout( const char *path, int timeout ) {
    int fd = -1;
    struct sigaction alarm_action = {
        .sa_handler = &alarm_handler,
    };
    struct flock lock = {
        .l_type = F_WRLCK,
        .l_whence = SEEK_SET,
    };

    fd = open( path, O_CREAT | O_RDWR, 0600 );
    if ( fd < 0 ) {
        /* create the required directory if necessary */
        char *s = strdup( path );
        char *t = strrchr( s, '/' );
        if ( t ) *t = '\0';
        t = NULL;
        asprintf( &t, "mkdir -p %s ; chmod 770 %s", s, s );
        if ( NULL != t ) {
            system( t );
            free( t );
        }
        free( s );
        fd = open( path, O_CREAT | O_RDWR, 0600 );
        if ( fd < 0 ) {
            ERROR( "cannot open `%s': %m\n", path );
            goto err;
        }
    }

    if ( sigaction( SIGALRM, &alarm_action, NULL ) < 0 ) {
        ERROR( "cannot set alarm handler: %m\n" );
        goto err;
    }

    alarm( timeout );

    if ( fcntl( fd, F_SETLKW, &lock ) < 0 ) {
        ERROR( "cannot lock `%s': %m\n", path );
        goto err;
    }

    if ( 0 ) {
err:
        if ( fd >= 0 )
            close( fd );
        fd = -1;
    }
    alarm( 0 );
    return fd;
}

static void delete_old_logfile( const char *filename, time_t current_time, time_t cut_off ) {
    struct stat filestat;
    if ( !stat( filename, &filestat ) ) {
        /* if the file exists; get its last modification time */
        /* older than cut_off ? */
        if ( current_time > filestat.st_mtime && ( current_time - filestat.st_mtime ) > cut_off )
            unlink( filename );
    }
}

static void usage( void ) {
    fprintf( stderr,
             "Usage: %s [OPTION]... [TYPE]...\n"
             "Collect statistics.\n"
             "\n"
             "Mandatory arguments to long options are mandatory for short options too.\n"
             "  -h, --help         display this help and exit\n"
             /* "  -l, --list-types ...\n" */
             /* describe */
             ,
             program_invocation_short_name );
}

static void dumpProcFile( FILE *f, const char *filename ) {
    static char tbuf[64 * 1024];
    int d = open( filename, O_RDONLY, 0 );
    int ret ;
    if ( 0 > d ) return;

    ret = read( d, tbuf, sizeof( tbuf ) - 1 );
    close( d );
    if ( 0 >= ret ) return;

    fprintf( f, "%s\n%d\n", filename, ret );
    fwrite( tbuf, sizeof( char ), ret, f );
    fprintf( f, "\n\n" );
}

int main( int argc, char *argv[] ) {
    int lock_fd = -1;
    int lock_timeout = 30;
    const char *current_path = STATS_DIR_PATH"/current";
    /* modified by charngda */
    const char *pid_path = STATS_DIR_PATH"/.pid";

    const char *mark = NULL;
    int rc = 0;
    size_t i;
    struct stats_type *type;

    struct option opts[] = {
        { "help", 0, 0, 'h' },
        { "mark", 0, 0, 'm' },
        { NULL, 0, 0, 0 },
    };

    int c;
    while ( ( c = getopt_long( argc, argv, "hm:", opts, 0 ) ) != -1 ) {
        switch ( c ) {
            case 'h':
                usage();
                exit( 0 );
            case 'm':
                mark = optarg;
                break;
            case '?':
                fprintf( stderr, "Try `%s --help' for more information.\n", program_invocation_short_name );
                exit( 1 );
        }
    }

    umask( 022 );

    if ( !( optind < argc ) )
        FATAL( "must specify one of the commands: begin, end, collect, rotate, mark, daemon\n" );

    /* modified by charngda */
    /* duplicate st->st_schema_def to st->orig_st_schema_def */
    i = 0;
    while ( ( type = stats_type_for_each( &i ) ) != NULL ) {
        type->orig_st_schema_def = type->st_schema_def;
    }

    const char *cmd_str = argv[optind];
    char **arg_list = argv + optind + 1;
    size_t arg_count = argc - optind - 1;

    enum {
        cmd_begin,
        cmd_collect,
        cmd_end,
        cmd_rotate,
        /* modified by charngda */
        cmd_daemon,
    } cmd;

    if ( strcmp( cmd_str, "begin" ) == 0 )
        cmd = cmd_begin;
    else if ( strcmp( cmd_str, "collect" ) == 0 )
        cmd = cmd_collect;
    else if ( strcmp( cmd_str, "end" ) == 0 )
        cmd = cmd_end;
    else if ( strcmp( cmd_str, "rotate" ) == 0 )
        cmd = cmd_rotate;
    else if ( strcmp( cmd_str, "daemon" ) == 0 )
        cmd = cmd_daemon;
    else
        FATAL( "invalid command `%s'\n", cmd_str );

    /* modified by charngda */
    /* daemonize */
    if ( cmd_daemon == cmd ) {
        /* kill existing processes */
        char *s = NULL;
        if ( !access( pid_path, F_OK ) ) {
            asprintf( &s, "cat %s | xargs kill -9 ; rm -f %s", pid_path, pid_path );
            system( s );
            free( s );
        }
        /* fork */
        pid_t pid = fork();
        if ( 0 > pid ) FATAL( "cannot fork\n" );
        if ( 0 < pid ) exit( 0 );
        /* create a unique session ID for the child process */
        //        if ( setsid() < 0 )   FATAL( "cannot setsid\n" );
        setsid();
        //        if ( chdir( "/" ) < 0 ) FATAL( "cannot change current working directory to '/'\n" );
        chdir( "/" );
    }

    lock_fd = open_lock_timeout( STATS_LOCK_PATH, lock_timeout );
    if ( lock_fd < 0 )
        FATAL( "cannot acquire lock. Are you sure there is no other %s running ?\n", argv[0] );

    if ( cmd == cmd_rotate ) {
        if ( unlink( current_path ) < 0 && errno != ENOENT ) {
            ERROR( "cannot unlink `%s': %m\n", current_path );
            rc = 1;
        }
        goto out;
    }

    current_time = time( NULL );
    /* pscanf( JOBID_FILE_PATH, "%79s", current_jobid ); */
    /* modified for CCR environment by charngda
       At CCR we have job files under JOBID_FILE_PATH directory,
       e.g.
         1737472.d15n41.ccr.buffalo.edu
     */
    {
        struct dirent *ent;
        DIR *dir = opendir( JOBID_FILE_PATH );
        if ( dir ) {
            current_jobid[0] = 0;
            char *t;
            while ( ( ent = readdir( dir ) ) != NULL ) {
                if ( !strstr( ent->d_name, "edu.JB" ) )
                    continue;
                t = strchr( ent->d_name, '.' );
                if ( t ) *t = 0;
                strcat( current_jobid, ent->d_name );
                strcat( current_jobid, "," );
            }
            if ( 0 == current_jobid[0] )
                strcpy( current_jobid, "0" );
            else {
                /* remove the last comma */
                current_jobid[strlen( current_jobid ) - 1] = 0;
            }
        }
    }

    nr_cpus = sysconf( _SC_NPROCESSORS_ONLN );

    if ( mkdir( STATS_DIR_PATH, 0777 ) < 0 ) {
        /* modified by charngda */
        /* use /bin/mkdir instead */
        if ( EEXIST != errno ) {
            char *s = NULL;
            asprintf( &s, "mkdir -p %s ; chgrp ccrstaff %s; chmod 770 %s", STATS_DIR_PATH, STATS_DIR_PATH, STATS_DIR_PATH );
            if ( NULL != s ) {
                system( s );
                free( s );
            }
        }
        if ( access( STATS_DIR_PATH, F_OK | W_OK | X_OK ) < 0 ) {
            FATAL( "cannot create directory `%s': %m\n", STATS_DIR_PATH );
        }
    }

    if ( cmd_daemon == cmd ) {
        /* modified by charngda */
        /* record current process Id */
        FILE *f = fopen( pid_path, "w" );
        if ( NULL == f ) FATAL( "cannot create file `%s': %m\n", pid_path );
        fprintf( f, "%d\n", getpid() );
        fclose( f );
        /* modified by charngda */
        close( STDIN_FILENO );
        close( STDOUT_FILENO );
        close( STDERR_FILENO );
    }

    struct stats_file sf;
DaemonLoopBeginHere:
    if ( cmd_daemon == cmd ) {
        /* modified by charngda */
        /* in daemon mode, we adopt the approach similar to sar, i.e.
           we open /var/log/tacc_stats/statXX
           where XX is today's day
           If this file is too old, we delete it (log rotation)
           and create a new one. (So we keep the logs up to a month)
         */
        /* wake up every 600 seconds and take readings */
        long toSleep = 600 - time( NULL ) % 600 + 3;
        if ( 0 < toSleep ) sleep( toSleep );

        current_time = time( NULL );
        struct tm *localTmp;
        char current_path[sizeof( STATS_DIR_PATH ) + 100];
        localTmp = localtime( &current_time );
        if ( NULL == localTmp )
            goto DaemonLoopBeginHere;
        if ( !strftime( current_path, sizeof( current_path ), STATS_DIR_PATH "/day%d", localTmp ) )
            goto DaemonLoopBeginHere;

        /* older than 1 week ? */
        delete_old_logfile( current_path,  current_time, 86400 * 7 ) ;
        if ( stats_file_open( &sf, current_path ) < 0 ) {
            goto DaemonLoopBeginHere;
        }
    }
    else {
        delete_old_logfile( current_path,  current_time, 86400 * 7 ) ;
        if ( stats_file_open( &sf, current_path ) < 0 ) {
            rc = 1;
            goto out;
        }
    }

    int enable_all = 0;
    int select_all = cmd != cmd_collect || arg_count == 0;

    if ( cmd_daemon != cmd ) {
        if ( sf.sf_empty ) {
            /* modified by charngda */
            struct tm *localTmp;
            localTmp = localtime( &current_time );
            char link_path[sizeof( STATS_DIR_PATH ) + 100];
            if ( !strftime( link_path, sizeof( link_path ), STATS_DIR_PATH "/day%d", localTmp ) )
                ERROR( "strftime failed: %m\n" );

            /* delete anything older than 1 week */
            int i;
            char old_log_path[sizeof( STATS_DIR_PATH ) + 100];
            for( i = 1; i <= 31; ++i ) {
                sprintf( old_log_path,  STATS_DIR_PATH "/day%02d", i );
                delete_old_logfile( old_log_path, current_time, 86400 * 7 );
            }
            if ( link( current_path, link_path ) < 0 ) {
                unlink( link_path );
                if ( link( current_path, link_path ) < 0 ) /* retry */
                    ERROR( "cannot link `%s' to `%s': %m\n", current_path, link_path );
            }
            enable_all = 1;
            select_all = 1;
        }
    }
    else {
        /* modified by charngda */
        /* always collect everything in daemon mode */
        enable_all = 1;
        select_all = 1;
    }

    if ( cmd == cmd_collect ) {
        /* If arg_count is zero then we select all below. */
        for ( i = 0; i < arg_count; i++ ) {
            type = stats_type_get( arg_list[i] );
            if ( type == NULL ) {
                ERROR( "unknown type `%s'\n", arg_list[i] );
                continue;
            }
            type->st_selected = 1;
        }
    }

    i = 0;
    while ( ( type = stats_type_for_each( &i ) ) != NULL ) {
        if ( enable_all )
            type->st_enabled = 1;

        if ( !type->st_enabled )
            continue;

        if ( stats_type_init( type ) < 0 ) {
            type->st_enabled = 0;
            continue;
        }

        if ( select_all )
            type->st_selected = 1;

        if ( cmd == cmd_begin && type->st_begin != NULL )
            ( *type->st_begin )( type );

        if ( type->st_enabled && type->st_selected )
            ( *type->st_collect )( type );

        /* modified by charngda */
        /* in daemon mode, call st_begin after each reading */
        if ( cmd == cmd_daemon && type->st_begin != NULL )
            ( *type->st_begin )( type );
    }

    if ( mark != NULL )
        stats_file_mark( &sf, "%s", mark );
    else if ( cmd == cmd_begin || cmd == cmd_end )
        /* On begin set mark to "begin JOBID", and similar for end. */
        stats_file_mark( &sf, "%s %s", cmd_str, arg_count > 0 ? arg_list[0] : "-" );

#if 0
    {
    /* added by charngda */
    /* store the output from ps */
       FILE *f = popen("/bin/ps -AFT|/bin/egrep -v '^(root|rpc|condor|postfix)'|/bin/gzip|base64 -w 0","r");
       if (f) {
          char *s = NULL;
          size_t n = 0;
          if (0 < getline(&s, &n, f)) {
            stats_file_mark( &sf, "ps %s", s );
            free(s);
          }
          pclose(f);
       }
    }
#endif

    /* added by charngda */
    /* archive stats & accounting info of processes of interest
       from /proc/<pid>/ */
    /* most of the code is from sysinfo.c of http://procps.sf.net */
    DIR *proc;
    if ( NULL != (proc = opendir( "/proc" )) ) {
        struct dirent *ent;
        int ret;
        char *tbuf = malloc( 64 * 1024 );
        char tmpFileName[] = "/tmp/tacc_stats_XXXXXX";
        mktemp(tmpFileName);

        /* pipe the result to gzip + base64 */
        sprintf(tbuf,"/bin/gzip - | /usr/bin/base64 -w 0 > %s",tmpFileName);
        FILE *f = popen(tbuf, "w" );
        if ( f ) {
            while( ( ent = readdir( proc ) ) ) {
                char *cp;
                int fd, nthreads = 0;
                if ( !isdigit( ent->d_name[0] ) ) continue; /* not a process */

                /* get the uid and #threads of the process, and ignore
                   processes owned by uid < 1000 */
                sprintf( tbuf, "/proc/%s/status", ent->d_name );
                fd = open( tbuf, O_RDONLY, 0 );
                if ( fd < 0 ) continue;
                ret = read( fd, tbuf, 64 * 1024 - 1 );
                close( fd );
                if ( 0 >= ret ) continue;

                cp = strstr( tbuf, "Threads:" );
                if ( cp ) {
                    if ( 1 != sscanf( cp + 8, "%d", &nthreads ) )
                        nthreads = 1;
                }

                cp = strstr( tbuf, "Uid:" );
                if ( !cp ) continue;
                if ( 1 == sscanf( cp + 4, "%d", &fd ) && 1000 < fd ) {
                    const char *procfiles[] = { "cmdline", "environ", "io", "numa_maps", "smaps", "stat", "stack"};
                    tbuf[ret] = '\0';
                    fprintf( f, "/proc/%s/status\n%d\n%s\n\n", ent->d_name, ret, tbuf );
                    for ( fd = 0; fd < sizeof( procfiles ) / sizeof( procfiles[0] ); ++fd ) {
                        /* archive other files under /proc */
                        sprintf( tbuf, "/proc/%s/%s", ent->d_name, procfiles[fd] );
                        dumpProcFile( f, tbuf );
                    }

                    if ( 1 < nthreads ) {
                        DIR *tasks;
                        sprintf( tbuf, "/proc/%s/task", ent->d_name );
                        if ( NULL != (tasks = opendir( tbuf )) ) {
                            struct dirent *ent2;
                            const char *taskfiles[] = { "stat", "status", "sched", "stack"};
                            while( ( ent2 = readdir( tasks ) ) ) {
                                if ( !isdigit( ent2->d_name[0] ) ) continue; /* not a task */
                                for ( fd = 0; fd < sizeof( taskfiles ) / sizeof( taskfiles[0] ); ++fd ) {
                                    sprintf( tbuf, "/proc/%s/task/%s/%s", ent->d_name, ent2->d_name, taskfiles[fd] );
                                    dumpProcFile( f, tbuf );
                                }
                            }
                            closedir( tasks );
                        }
                    }
                }
            }
            pclose(f);
        }
        /* clean up */
        closedir( proc );
        free( tbuf );

        /* get the result of gzip + base64 */
        f = fopen(tmpFileName,"r");
        if (f) {
          char *s = NULL;
          size_t n;
          if (0 < getline(&s, &n, f)) {
            /* and store them in the tacc_stats log */
            stats_file_mark( &sf, "procdump %s", s );
            free(s);
          }
          fclose(f);
        }
        unlink(tmpFileName);
    }

    if ( stats_file_close( &sf ) < 0 )
        rc = 1;

    /* Cleanup. */
    i = 0;
    while ( ( type = stats_type_for_each( &i ) ) != NULL )
        stats_type_destroy( type );

    if ( cmd_daemon == cmd ) goto DaemonLoopBeginHere;

out:
    return rc;
}
