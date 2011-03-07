CC = gcc
CFLAGS = -Wall -Werror
CPPFLAGS = -g -DDEBUG

ST_OBJS := st_block.o st_cpu.o st_ib.o st_job.o st_lustre.o st_mem.o st_net.o \
 st_perf_amd64.o st_ps.o st_vm.o
OBJS := stats.o dict.o collect.o split.o stats_file.o main.o test.o test-loop.o $(ST_OBJS)

all: main test test-loop

main: main.o stats.o dict.o collect.o split.o stats_file.o $(ST_OBJS)

test: test.o stats.o dict.o collect.o split.o stats_file.o $(ST_OBJS)

test-loop: test-loop.o stats.o dict.o collect.o split.o stats_file.o $(ST_OBJS)

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

stats.h: stats.x
	sort --check stats.x
	touch stats.h

.PHONY: clean
clean:
	rm -f test $(OBJS) $(OBJS:%.o=.%.d)
