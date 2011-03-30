#!/usr/bin/awk -f

# ST_OBJS-$(CONFIG_ST_AMD64_PMC) += st_amd64_pmc.o
# ST_FLAGS-$(CONFIG_ST_AMD64_PMC) += -DCONFIG_ST_AMD64_PMC=1

{
  printf "ST_OBJS_$(CONFIG_ST_%s) += st_%s.o\n", $1, tolower($1);
  printf "ST_FLAGS_$(CONFIG_ST_%s) += -DCONFIG_ST_%s=1\n", $1, $1;
}
