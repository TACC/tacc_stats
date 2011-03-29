#ifndef _SCHEMA_H_
#define _SCHEMA_H_

#define SE_EVENT 1
#define SE_BITS 2

struct schema_entry {
  char *se_unit;
  char *se_desc;
  unsigned int se_index:16;
  unsigned int se_type:8;
  unsigned int se_width:8;
  char se_key[];
};

struct stats_type;

int stats_type_set_schema(struct stats_type *type, char *str);

#endif
