CC = gcc
CPPFLAGS = $(CDEBUG)
CFLAGS = -Wall

test: test.o stats.o dict.o read_key_value.o read_single.o st_cpu.o st_ib.o st_job.o st_lustre.o st_mem.o st_ps.o st_vm.o

clean:
	rm -f test *.o
