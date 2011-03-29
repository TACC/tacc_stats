#ifndef _SCHEMA_H_
#define _SCHEMA_H_

#define SE_EVENT 1
#define SE_BITS 2

struct schema_entry {
  char *se_unit;
  char *se_desc;
  unsigned int se_index;
  unsigned int se_type;
  unsigned int se_width;
  char se_key[];
};

static inline struct schema_entry *key_to_schema_entry(const char *key)
{
  /* Cannot be replaced with sizeof(*se), (due to alignment) at least with 3.4.6. */
  size_t se_key_offset = (((struct schema_entry *) NULL)->se_key) - (char *) NULL;
  return (struct schema_entry *) (key - se_key_offset);
}

struct stats_type;

int stats_type_set_schema(struct stats_type *type, const char *str);




#endif
