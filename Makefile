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

edit = sed \
 -e 's|@bindir[@]|$(bindir)|g' \
 -e 's|@prefix[@]|$(prefix)|g'
# logdir

# @stats_cron_path@

include config

# sed -rn 's/X\(([^)]+)\)/CPPFLAGS_$(\1) += -D\1=1/p' stats.x
CPPFLAGS_$(CONFIG_AMD64_PMC) += -DCONFIG_AMD64_PMC=1
CPPFLAGS_$(CONFIG_BLOCK) += -DCONFIG_BLOCK=1
CPPFLAGS_$(CONFIG_CPU) += -DCONFIG_CPU=1
CPPFLAGS_$(CONFIG_IB) += -DCONFIG_IB=1
CPPFLAGS_$(CONFIG_IB_EXT) += -DCONFIG_IB_EXT=1
CPPFLAGS_$(CONFIG_INTEL_PMC3) += -DCONFIG_INTEL_PMC3=1
CPPFLAGS_$(CONFIG_INTEL_UNCORE) += -DCONFIG_INTEL_UNCORE=1
CPPFLAGS_$(CONFIG_LLITE) += -DCONFIG_LLITE=1
CPPFLAGS_$(CONFIG_LUSTRE) += -DCONFIG_LUSTRE=1
CPPFLAGS_$(CONFIG_MEM) += -DCONFIG_MEM=1
CPPFLAGS_$(CONFIG_NET) += -DCONFIG_NET=1
CPPFLAGS_$(CONFIG_PS) += -DCONFIG_PS=1
CPPFLAGS_$(CONFIG_SYSV_SHM) += -DCONFIG_SYSV_SHM=1
CPPFLAGS_$(CONFIG_VFS) += -DCONFIG_VFS=1
CPPFLAGS_$(CONFIG_VM) += -DCONFIG_VM=1

OBJS_$(CONFIG_AMD64_PMC) += amd64_pmc.o
OBJS_$(CONFIG_BLOCK) += block.o
OBJS_$(CONFIG_CPU) += cpu.o
OBJS_$(CONFIG_IB) += ib.o
OBJS_$(CONFIG_IB_EXT) += ib_ext.o
OBJS_$(CONFIG_INTEL_PMC3) += intel_pmc3.o
OBJS_$(CONFIG_INTEL_UNCORE) += intel_uncore.o
OBJS_$(CONFIG_LLITE) += llite.o
OBJS_$(CONFIG_LUSTRE) += lustre.o
OBJS_$(CONFIG_MEM) += mem.o
OBJS_$(CONFIG_NET) += net.o
OBJS_$(CONFIG_PS) += ps.o
OBJS_$(CONFIG_SYSV_SHM) += sysv_shm.o
OBJS_$(CONFIG_VM) += vm.o
OBJS_$(CONFIG_VFS) += vfs.o

CPPFLAGS_$(CONFIG_IB) += -I/opt/ofed/include
CPPFLAGS_$(CONFIG_IB_EXT) += -I/opt/ofed/include

LDFLAGS_$(CONFIG_IB) += -L/opt/ofed/lib64 -libmad
LDFLAGS_$(CONFIG_IB_EXT) += -L/opt/ofed/lib64 -libmad

tacc_stats: $(OBJS) $(OBJS_y)
	$(CC) $(LDFLAGS) $(LDFLAGS_y) $(OBJS) $(OBJS_y) -o $@

init.d/tacc_stats: init.d/tacc_stats.in
	$(edit) init.d/tacc_stats.in > init.d/tacc_stats

-include $(OBJS_y:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $(CPPFLAGS_y) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $(CPPFLAGS_y) $*.c > .$*.d

.PHONY: clean
clean:
	rm -f tacc_stats $(OBJS) $(OBJS_y)
