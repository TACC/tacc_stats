stats_program = tacc_stats
stats_version = 1.0.0
# stats_dir = /var/log/tacc_stats
# stats_cron_interval = 10 # minutes
jobid_path = /var/run/TACC_jobid

CC = gcc
CFLAGS = -Wall -Werror -DDEBUG # XXX
CPPFLAGS = -D_GNU_SOURCE \
 -DSTATS_PROGRAM=\"$(stats_program)\" \
 -DSTATS_VERSION=\"$(stats_version)\" \
 -DJOBID_PATH=\"$(jobid_path)\"
LDFLAGS = -lrt
OBJS = main.o stats.o dict.o collect.o schema.o stats_file.o
TYPES = amd64_pmc block cpu ib ib_ext intel_pmc3 intel_uncore llite lustre mem net ps sysv_shm tmpfs vfs vm

edit = sed \
 -e 's|@bindir[@]|$(bindir)|g' \
 -e 's|@prefix[@]|$(prefix)|g'
# logdir
# @stats_cron_path@

-include config

all: tacc_stats

# The road to Hell is paved with elaborate Makefile constructs.

stats.x: config
	@echo "$(foreach t,$(TYPES), $(if $($(t)),X($(t)),))" > stats.x

OBJS += $(foreach t,$(TYPES), $(if $($(t)),$(t).o,))

ib_x = $(or $(ib),$(ib_ext))
ifdef ib_x
CPPFLAGS += -I/opt/ofed/include
LDFLAGS += -L/opt/ofed/lib64 -libmad
endif

tacc_stats: $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@

init.d/tacc_stats: init.d/tacc_stats.in
	$(edit) init.d/tacc_stats.in > init.d/tacc_stats

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

.PHONY: clean
clean:
	rm -f tacc_stats $(OBJS)
