stats_program = tacc_stats
stats_version = 1.0.0
# stats_dir = /var/log/tacc_stats
# stats_cron_interval = 10 # minutes
jobid_path = /var/run/TACC_jobid

CC = gcc
CFLAGS = -Wall -Werror
CPPFLAGS = -D_GNU_SOURCE \
 -DSTATS_PROGRAM=\"$(stats_program)\" \
 -DSTATS_VERSION=\"$(stats_version)\" \
 -DJOBID_PATH=\"$(jobid_path)\"
LDFLAGS = -lrt

CPPFLAGS += -I/opt/ofed/include
LDFLAGS += -L/opt/ofed/lib64 -libmad

edit = sed \
 -e 's|@bindir[@]|$(bindir)|g' \
 -e 's|@prefix[@]|$(prefix)|g'
# logdir

# @stats_cron_path@

-include config

OBJS_$(CONFIG_AMD64_PMC) += amd64_pmc.o
OBJS_$(CONFIG_BLOCK) += block.o
OBJS_$(CONFIG_CPU) += cpu.o
OBJS_$(CONFIG_FS) += fs.o
OBJS_$(CONFIG_IB) += ib.o
OBJS_$(CONFIG_IB_EXT) += ib_ext.o
OBJS_$(CONFIG_INTEL_PMC3) += intel_pmc3.o
OBJS_$(CONFIG_INTEL_UNCORE) += intel_uncore.o
OBJS_$(CONFIG_LLITE) += llite.o
OBJS_$(CONFIG_LUSTRE) += lustre.o
OBJS_$(CONFIG_MEM) += mem.o
OBJS_$(CONFIG_NET) += net.o
OBJS_$(CONFIG_PS) += ps.o
OBJS_$(CONFIG_VM) += vm.o

OBJS := main.o stats.o dict.o collect.o schema.o stats_file.o $(OBJS_y)

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
