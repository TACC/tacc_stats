#ifndef _DICT_H_
#define _DICT_H_
#include <stddef.h>

typedef unsigned long hash_t;
hash_t dict_strhash(const char *s);

#define DICT_HASH_DUMMY (((hash_t) 1) << (8 * sizeof(hash_t) - 1))

struct dict_entry {
  hash_t d_hash;
  char *d_key;
};

struct dict {
  struct dict_entry *d_table;
  size_t d_mask;
  size_t d_load;
  size_t d_count;
};

int dict_init(struct dict *dict, size_t count);
void dict_destroy(struct dict *dict);

struct dict_entry *dict_entry_ref(struct dict *dict, hash_t hash, const char *key);
int dict_entry_set(struct dict *dict, struct dict_entry *ent, hash_t hash, char *key);
char *dict_ent_remv(struct dict *dict, struct dict_entry *ent, int may_resize);
struct dict_entry *dict_for_each(struct dict *dict, size_t *i);
/* void dict_resize(struct dict *dict, int force); */

char *dict_ref(struct dict *dict, const char *key);
int dict_set(struct dict *dict, char *key);

#endif
