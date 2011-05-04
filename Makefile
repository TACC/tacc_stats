-include config
CC = gcc
CFLAGS = -Wall -Werror # -pg
CPPFLAGS = -D_GNU_SOURCE -I/opt/ofed/include -DEPREFIX='"/sge_common/default/tacc/tacc_stats_test"' # -DDEBUG # -g
LDFLAGS = -L/opt/ofed/lib64 -libmad # -pg

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

OBJS := stats.o dict.o collect.o schema.o tacc_stats.o helper.o stats_file.o \
  stats_aggr.o $(OBJS_y)

all: tacc_stats

tacc_stats: tacc_stats.o helper.o stats.o schema.o dict.o collect.o stats_file.o $(OBJS_y)

stats_aggr_test: stats_aggr_test.o stats_aggr.o

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

.PHONY: clean
clean:
	rm -f tacc_stats $(OBJS)
