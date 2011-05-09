#include <malloc.h>
#include <string.h>
#include <ctype.h>
#include "stats.h"
#include "dict.h"
#include "trace.h"
#include "schema.h"

/* key,opt1[=arg],opt2,... */

struct schema_entry *parse_schema_entry(char *str)
{
  struct schema_entry *se = NULL;

  while (isspace(*str))
    str++;

  char *key = strsep(&str, ",");
  if (*key == 0)
    return NULL;

  se = malloc(sizeof(*se) + strlen(key) + 1);
  if (se == NULL)
    return NULL;

  memset(se, 0, sizeof(*se));
  strcpy(se->se_key, key);

  while (str != NULL) {
    char *opt = strsep(&str, ",");
    char *opt_arg = opt;
    strsep(&opt_arg, "=");

    switch (toupper(*opt)) { /* XXX toupper() */
    default:
      TRACE("unknown schema option `%s'\n", opt);
      break;
    case 'B':
      se->se_type = SE_BITS;
      break;
    case 'D':
      if (opt_arg != NULL && strlen(opt_arg) != 0) /* XXX */
        se->se_desc = strdup(opt_arg);
      break;
    case 'E':
      se->se_type = SE_EVENT;
      break;
    case 'U':
      if (opt_arg != NULL)
        se->se_unit = strdup(opt_arg);
      break;
    case 'W':
      if (opt_arg != NULL)
        se->se_width = strtoul(opt + 1, NULL, 0);
      break;
    }
  }

  TRACE("se_key `%s', se_type %u, se_width %u, se_unit %s, se_desc `%s'\n",
        se->se_key, se->se_type, se->se_width,
        se->se_unit ? : "NONE", se->se_desc ? : "NONE");

  return se;
}

int schema_init(struct schema *sc, const char *def)
{
  int rc = -1;
  size_t nr_se = 0;
  char *cpy = strdup(def);

  while (cpy != NULL) {
    while (isspace(*cpy))
      cpy++;

    char *tok = strsep(&cpy, " ");
    if (*tok == 0)
      continue;

    struct schema_entry *se = parse_schema_entry(tok);
    if (se == NULL)
      goto err;

    se->se_index = nr_se++;
    if (dict_set(&sc->sc_dict, se->se_key) < 0)
      goto err;
  }

  sc->sc_len = nr_se;
  sc->sc_ent = calloc(sc->sc_len, sizeof(*sc->sc_ent));
  if (sc->sc_ent == NULL && sc->sc_len != 0) {
    ERROR("cannot allocate schema entries: %m\n");
    goto err;
  }

  size_t i = 0;
  char *key;
  while ((key = dict_for_each(&sc->sc_dict, &i)) != NULL) {
    struct schema_entry *se = key_to_schema_entry(key);
    sc->sc_ent[se->se_index] = se;
    TRACE("i %zu, d_key `%s', se_key `%s', se_index %u\n", i, key, se->se_key, se->se_index);
  }

  rc = 0;
 err:
  free(cpy);
  return rc;
}
