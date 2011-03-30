CC = gcc
CFLAGS = -Wall -Werror # -pg
CPPFLAGS = -D_GNU_SOURCE -I/opt/ofed/include -DEPREFIX='"/sge_common/default/tacc/tacc_stats_test"' # -DDEBUG # -g
LDFLAGS = -L/opt/ofed/lib64 -libmad # -pg

-include config
-include rules

OBJS := $(ST_OBJS_y) stats.o dict.o collect.o schema.o \
 tacc_stats.o helper.o stats_file.o stats_aggr.o

CPPFLAGS += $(ST_FLAGS_y)

all: tacc_stats

tacc_stats: tacc_stats.o helper.o stats.o schema.o dict.o collect.o stats_file.o $(ST_OBJS_y)

stats_aggr_test: stats_aggr_test.o stats_aggr.o

-include $(OBJS:%.o=.%.d)

%.o: %.c
	$(CC) -c $(CFLAGS) $(CPPFLAGS) $*.c -o $*.o
	$(CC) -MM $(CFLAGS) $(CPPFLAGS) $*.c > .$*.d

stats.x: stats.all
	sort stats.all | awk '{ printf "#ifdef CONFIG_ST_%s\nX(%s)\n#endif\n", $1, $1; }'

.PHONY: clean
clean:
	rm -f tacc_stats $(OBJS) $(OBJS:%.o=.%.d)
