#include <stddef.h>
#include <string.h>
#include <malloc.h>
#include "dict.h"

/* Stolen from Python's stringobject.c.  GPL. */
// static long
// string_hash(PyStringObject *a)
// {
//   register Py_ssize_t len;
//   register unsigned char *p;
//   register long x;
//
//   if (a->ob_shash != -1)
//     return a->ob_shash;
//   len = Py_SIZE(a);
//   p = (unsigned char *) a->ob_sval;
//   x = *p << 7;
//   while (--len >= 0)
//     x = (1000003*x) ^ *p++;
//   x ^= Py_SIZE(a);
//   if (x == -1)
//     x = -2;
//   a->ob_shash = x;
//   return x;
// }

hash_t dict_strhash(const char *s)
{
  const unsigned char *p = (const unsigned char *) s;
  hash_t x = *p << 7;

  for (; *p != 0; p++)
    x = (1000003 * x) ^ *p;

  x ^= p - (const unsigned char *) s;

  return x & ~DICT_HASH_DUMMY;
}

#define DICT_TABLE_SIZE_MIN 8
#define DICT_TABLE_SIZE_MAX (((size_t) 1) << (8 * sizeof(size_t) - 1))
#define PERTURB_SHIFT 5

int dict_init(struct dict *dict, size_t count)
{
  size_t table_size = DICT_TABLE_SIZE_MIN;

  /* Need count < 2/3 of table_size. */
  while (table_size < DICT_TABLE_SIZE_MAX && 3 * count >= 2 * table_size)
    table_size *= 2;

  memset(dict, 0, sizeof(struct dict));
  dict->d_table = calloc(table_size, sizeof(struct dict_entry));
  if (dict->d_table == NULL)
    return -1;

  dict->d_mask = table_size - 1;
  return 0;
}

void dict_destroy(struct dict *dict)
{
  free(dict->d_table);
}

int dict_resize(struct dict *dict, size_t new_table_size)
{
  struct dict_entry *table, *old_table;
  size_t mask, old_table_size;

  table = calloc(new_table_size, sizeof(struct dict_entry));
  if (table == NULL)
    return -1;

  old_table = dict->d_table;
  old_table_size = dict->d_mask + 1;

  dict->d_table = table;
  dict->d_mask = mask = new_table_size - 1;
  dict->d_load = dict->d_count;

  size_t i, j;
  for (j = 0; j < old_table_size; j++) {
    hash_t hash = old_table[j].d_hash;
    char *key = old_table[j].d_key;

    if (key == NULL || (hash & DICT_HASH_DUMMY))
      continue;

    size_t perturb = hash;
    i = hash & mask;

    while (table[i & mask].d_key != NULL) {
      i = (i << 2) + i + perturb + 1;
      perturb >>= PERTURB_SHIFT;
    }

    table[i & mask].d_hash = hash;
    table[i & mask].d_key = key;
  }

  free(old_table);

  return 0;
}

struct dict_entry *dict_ref(struct dict *dict, hash_t hash, const char *key)
{
  size_t mask, i, perturb;
  struct dict_entry *table, *dummy, *ent;

  mask = dict->d_mask;
  table = dict->d_table;
  dummy = NULL;

  i = hash & mask;
  ent = &table[i];

  /* TODO Check for ent->d_hash == hash first. */
  if (ent->d_hash & DICT_HASH_DUMMY)
    dummy = ent;
  else if (ent->d_key == NULL)
    return ent;
  else if (ent->d_hash == hash && strcmp(ent->d_key, key) == 0)
    return ent;

  perturb = hash;
  while (1) {
    i = (i << 2) + i + perturb + 1;
    ent = &table[i & mask];

    if (ent->d_hash & DICT_HASH_DUMMY) {
      if (dummy == NULL)
        dummy = ent;
    } else if (ent->d_key == NULL) {
      return (dummy != NULL) ? dummy : ent;
    } else if (ent->d_hash == hash && strcmp(ent->d_key, key) == 0) {
      return ent;
    }

    perturb >>= PERTURB_SHIFT;
  }
}

int dict_set(struct dict *dict, struct dict_entry *ent, hash_t hash, char *key)
{
  if (ent->d_key == NULL) {
    if (!(ent->d_hash & DICT_HASH_DUMMY)) {
      size_t table_size = dict->d_mask + 1;
      size_t load = dict->d_load + 1;

      if (2 * table_size <= 3 * load) {
        size_t count = dict->d_count + 1;
        while (table_size < DICT_TABLE_SIZE_MAX && 2 * table_size <= 3 * count)
          table_size *= 2;

        if (count >= table_size)
          return -1;

        if (dict_resize(dict, table_size) < 0)
          return -1;

        ent = dict_ref(dict, hash, key);
      }
      dict->d_load++;
    }

    ent->d_hash = hash;
    ent->d_key = key;
    dict->d_count++;
  }

  return 0;
}

char *dict_remv(struct dict *dict, struct dict_entry *ent, int may_resize)
{
  char *key = ent->d_key;
  if (key != NULL) {
    ent->d_hash = DICT_HASH_DUMMY;
    ent->d_key = NULL;
    dict->d_count--;
    if (may_resize) {
      /* TODO Shrink table if needed. */
    }
  }

  return key;
}

char *dict_lookup(struct dict *dict, const char *key)
{
  hash_t hash = dict_strhash(key);
  struct dict_entry *ent = dict_ref(dict, hash, key);

  if (ent->d_hash & DICT_HASH_DUMMY) /* Do we need this? */
    return NULL;

  return ent->d_key;
}

char **dict_search(struct dict *dict, char *key)
{
  hash_t hash = dict_strhash(key);
  struct dict_entry *ent = dict_ref(dict, hash, key);

  if (ent->d_key == NULL) {
    if (!(ent->d_hash & DICT_HASH_DUMMY)) {
      size_t table_size = dict->d_mask + 1;
      size_t load = dict->d_load + 1;

      if (2 * table_size <= 3 * load) {
        size_t count = dict->d_count + 1;
        while (table_size < DICT_TABLE_SIZE_MAX && 2 * table_size <= 3 * count)
          table_size *= 2;

        if (count == table_size)
          return NULL;

        if (dict_resize(dict, table_size) < 0)
          return NULL;

        ent = dict_ref(dict, hash, key);
      }
      dict->d_load++;
    }

    ent->d_hash = hash;
    ent->d_key = key;
    dict->d_count++;
  }

  return &ent->d_key;
}

struct dict_entry *dict_for_each(struct dict *dict, size_t *i)
{
  struct dict_entry *table = dict->d_table;
  size_t table_size = dict->d_mask + 1;

  while (*i < table_size) {
    struct dict_entry *ent = &table[*i];
    (*i)++;
    if (ent->d_key != NULL)
      return ent;
  }

  return NULL;
}
