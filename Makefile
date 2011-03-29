CC = gcc
CFLAGS = -Wall -Werror # -pg
CPPFLAGS = -D_GNU_SOURCE -I/opt/ofed/include -DDEBUG # -g
LDFLAGS = -L/opt/ofed/lib64 -libmad # -pg

ST_OBJS := st_amd64_pmc.o st_block.o st_cpu.o st_fs.o st_ib.o st_ib_ext.o \
 st_intel_pmc3.o st_intel_uncore.o st_lustre.o st_mem.o st_net.o \
 st_ps.o st_vm.o

OBJS :=  $(ST_OBJS) stats.o dict.o collect.o split.o readstr.o stats_file.o \
 tacc_stats.o stats_aggr.o schema.o

all: tacc_stats

tacc_stats: tacc_stats.o stats.o schema.o dict.o collect.o split.o readstr.o stats_file.o $(ST_OBJS)

stats_aggr_test: stats_aggr_test.o stats_aggr.o

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

stats.h: stats.x
	sort --check stats.x
	touch stats.h

.PHONY: clean
clean:
	rm -f tacc_stats $(OBJS) $(OBJS:%.o=.%.d)
