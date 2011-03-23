CC = gcc
CFLAGS = -Wall -Werror # -pg
CPPFLAGS = -D_GNU_SOURCE # -DDEBUG -g
LDFLAGS = # -pg

ST_OBJS := st_block.o st_cpu.o st_fs.o st_ib.o st_lustre.o st_mem.o st_net.o \
 st_perf_amd64.o st_perf_nehalem.o st_ps.o st_vm.o
OBJS :=  $(ST_OBJS) stats.o dict.o collect.o split.o readstr.o stats_file.o \
 tacc_stats.o test.o loop.o

all: tacc_stats test loop

tacc_stats: tacc_stats.o stats.o dict.o collect.o split.o readstr.o stats_file.o $(ST_OBJS)

test: test.o stats.o dict.o collect.o split.o stats_file.o $(ST_OBJS)

loop: loop.o stats.o dict.o collect.o split.o stats_file.o $(ST_OBJS)

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

stats.h: stats.x
	sort --check stats.x
	touch stats.h

.PHONY: clean
clean:
	rm -f tacc_stats test loop $(OBJS) $(OBJS:%.o=.%.d)
