stats_program = tacc_stats
stats_version = 1.0.0
# stats_dir = /var/log/tacc_stats
# stats_cron_interval = 10 # minutes
jobid_path = /var/run/TACC_jobid

CC = gcc
CFLAGS = -Wall -Werror -O3 # -DDEBUG
CPPFLAGS = -D_GNU_SOURCE \
 -DSTATS_PROGRAM=\"$(stats_program)\" \
 -DSTATS_VERSION=\"$(stats_version)\" \
 -DJOBID_PATH=\"$(jobid_path)\"
OBJS = main.o stats.o dict.o collect.o schema.o stats_file.o

EDIT = sed \
 -e 's|@bindir[@]|$(bindir)|g' \
 -e 's|@prefix[@]|$(prefix)|g'
# logdir
# @stats_cron_path@

-include config

all: tacc_stats

stats.x: config
	echo '$(patsubst %,X(%),$(sort $(TYPES)))' > stats.x

OBJS += $(patsubst %,%.o,$(TYPES))

tacc_stats: $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

init.d/tacc_stats: init.d/tacc_stats.in
	$(EDIT) init.d/tacc_stats.in > init.d/tacc_stats

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

.PHONY: clean
clean:
	rm -f tacc_stats $(OBJS)
