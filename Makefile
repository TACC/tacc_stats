name = tacc_stats
version = 1.0.1
stats_dir = /var/log/tacc_stats
stats_lock = /var/lock/tacc_stats
jobid_file = /var/run/TACC_jobid
config = config
-include $(config)

CC = gcc
CFLAGS = -Wall -Werror -O3 # -DDEBUG
CPPFLAGS = -D_GNU_SOURCE \
 -DSTATS_PROGRAM=\"$(name)\" \
 -DSTATS_VERSION=\"$(version)\" \
 -DSTATS_DIR_PATH=\"$(stats_dir)\" \
 -DSTATS_LOCK_PATH=\"$(stats_lock)\" \
 -DJOBID_FILE_PATH=\"$(jobid_file)\"

OBJS = main.o stats.o dict.o collect.o schema.o stats_file.o
OBJS += $(patsubst %,%.o,$(TYPES))

$(name): $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

stats.o: stats.x

stats.x: $(config)
	echo '$(patsubst %,X(%),$(sort $(TYPES)))' > stats.x

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

.PHONY: clean
clean:
	rm -f tacc_stats $(OBJS) $(OBJS:%.o=.%.d)
