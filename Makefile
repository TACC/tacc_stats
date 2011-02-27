CC = gcc
CPPFLAGS = $(CDEBUG)
CFLAGS = -Wall

test: test.o stats.o read_proc_stat.o read_meminfo.o read_loadavg.o read_vmstat.o read_ib_stats.o read_jobid.o

clean:
	rm -f test *.o
