name = tacc_stats
version = 1.0.2
stats_dir = /var/log/tacc_stats
stats_lock = /var/lock/tacc_stats
jobid_file = /var/spool/pbs/mom_priv/jobs/
config = config

CC = gcc
CFLAGS = -Wall -Werror -O3 # -DDEBUG
CPPFLAGS = -D_GNU_SOURCE \
 -DSTATS_PROGRAM=\"$(name)\" \
 -DSTATS_VERSION=\"$(version)\" \
 -DSTATS_DIR_PATH=\"$(stats_dir)\" \
 -DSTATS_LOCK_PATH=\"$(stats_lock)\" \
 -DJOBID_FILE_PATH=\"$(jobid_file)\"

#NCPUS = 64

-include $(config)

#OBJS = main.o stats.o dict.o collect.o schema.o stats_file.o lustre_obd_to_mnt.o
OBJS = main.o stats.o dict.o collect.o schema.o stats_file.o
OBJS += $(patsubst %,%.o,$(TYPES))

$(name): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

stats.o: stats.x

stats.x: $(config)
	echo '$(patsubst %,X(%),$(sort $(TYPES)))' > stats.x

irq.o: irq.c
	m4 -DNCPUS=$(NCPUS) $*.c | $(CC) -c $(CFLAGS) $(CPPFLAGS) -o $*.o -x c -

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

.PHONY: clean
clean:
	rm -f tacc_stats $(OBJS) $(OBJS:%.o=.%.d)
	rm *.o
