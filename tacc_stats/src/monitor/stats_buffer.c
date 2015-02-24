#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <ctype.h>
#include <limits.h>
#include <stdarg.h>
#include <sys/utsname.h>
#include <syslog.h>

#ifdef RMQ
#include <amqp_tcp_socket.h>
#include <amqp.h>
#include <amqp_framing.h>
#endif

#include "stats.h"
#include "stats_buffer.h"
#include "schema.h"
#include "trace.h"
#include "pscanf.h"
#include "string1.h"

#define SF_SCHEMA_CHAR '!'
#define SF_DEVICES_CHAR '@'
#define SF_COMMENT_CHAR '#'
#define SF_PROPERTY_CHAR '$'
#define SF_MARK_CHAR '%'


#define sf_printf(sf, fmt, args...) do {			\
    char *tmp_string = sf->sf_data;				\
    asprintf(&(sf->sf_data), "%s"fmt, sf->sf_data, ##args);	\
    free(tmp_string);						\
  } while(0)

#ifdef RMQ
static int send(struct stats_buffer *sf)
{
  int status;
  char const *exchange;
  char const *routingkey;
  amqp_socket_t *socket = NULL;
  amqp_connection_state_t conn;
  exchange = "amq.direct";
  routingkey = "tacc_stats";
  conn = amqp_new_connection();
  socket = amqp_tcp_socket_new(conn);
  status = amqp_socket_open(socket, sf->sf_host, atoi(sf->sf_port));
  amqp_login(conn, "/", 0, 131072, 0, AMQP_SASL_METHOD_PLAIN, 
	     "guest", "guest");
  amqp_channel_open(conn, 1);
  amqp_get_rpc_reply(conn);

  {
    amqp_basic_properties_t props;
    props._flags = AMQP_BASIC_CONTENT_TYPE_FLAG | AMQP_BASIC_DELIVERY_MODE_FLAG;
    props.content_type = amqp_cstring_bytes("text/plain");
    props.delivery_mode = 2; /* persistent delivery mode */
    amqp_basic_publish(conn,
		       1,
		       amqp_cstring_bytes(exchange),
		       amqp_cstring_bytes(routingkey),
		       0,
		       0,
		       &props,
		       amqp_cstring_bytes(sf->sf_data));
  }
  amqp_channel_close(conn, 1, AMQP_REPLY_SUCCESS);
  amqp_connection_close(conn, AMQP_REPLY_SUCCESS);
  amqp_destroy_connection(conn); 

  return 0;
}
#else
static int send(struct stats_buffer *sf) {
  syslog(LOG_INFO, "%s\n", sf->sf_data);
  return 0;
}
#endif

int stats_wr_hdr(struct stats_buffer *sf)
{
  struct utsname uts_buf;
  unsigned long long uptime = 0;
  
  uname(&uts_buf);
  pscanf("/proc/uptime", "%llu", &uptime);
  
  sf->sf_data = strdup("");

  sf_printf(sf, "%c%s %s\n", SF_PROPERTY_CHAR, STATS_PROGRAM, STATS_VERSION);
  sf_printf(sf, "%chostname %s\n", SF_PROPERTY_CHAR, uts_buf.nodename);
  sf_printf(sf, "%cuname %s %s %s %s\n", SF_PROPERTY_CHAR, uts_buf.sysname,
            uts_buf.machine, uts_buf.release, uts_buf.version);
  sf_printf(sf, "%cuptime %llu\n", SF_PROPERTY_CHAR, uptime);
  
  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (!type->st_enabled)
      continue;

    TRACE("type %s, schema_len %zu\n", type->st_name, type->st_schema.sc_len);

    /* Write schema. */
    sf_printf(sf, "%c%s", SF_SCHEMA_CHAR, type->st_name);

    /* MOVEME */
    size_t j;
    for (j = 0; j < type->st_schema.sc_len; j++) {
      struct schema_entry *se = type->st_schema.sc_ent[j];
      sf_printf(sf, " %s", se->se_key);
      if (se->se_type == SE_CONTROL)
        sf_printf(sf, ",C");
      if (se->se_type == SE_EVENT)
        sf_printf(sf, ",E");
      if (se->se_unit != NULL)
        sf_printf(sf, ",U=%s", se->se_unit);
      if (se->se_width != 0)
        sf_printf(sf, ",W=%u", se->se_width);
    }
    sf_printf(sf, "\n");
  }

  send(sf);
  free(sf->sf_data);
  return 0;
}

int stats_buffer_open(struct stats_buffer *sf)
{
  int rc = 0;
  memset(sf, 0, sizeof(*sf));
  return rc;
}

int stats_buffer_mark(struct stats_buffer *sf, const char *fmt, ...)
{
  /* TODO Concatenate new mark with old. */
  va_list args;
  va_start(args, fmt);

  if (vasprintf(&sf->sf_mark, fmt, args) < 0)
    sf->sf_mark = NULL;

  va_end(args);
  return 0;
}

int stats_buffer_write(struct stats_buffer *sf)
{
  int rc = 0;
  sf->sf_data=strdup("");

  struct utsname uts_buf;
  uname(&uts_buf);

  sf_printf(sf, "\n%f %s %s\n", current_time, current_jobid, uts_buf.nodename);

  /* Write mark. */
  if (sf->sf_mark != NULL) {
    const char *str = sf->sf_mark;
    while (*str != 0) {
      const char *eol = strchrnul(str, '\n');
      sf_printf(sf, "%c%*s\n", SF_MARK_CHAR, (int) (eol - str), str);
      str = eol;
      if (*str == '\n')
        str++;
    }
  }

  /* Write stats. */
  size_t i = 0;
  struct stats_type *type;
  while ((type = stats_type_for_each(&i)) != NULL) {
    if (!(type->st_enabled && type->st_selected))
      continue;

    size_t j = 0;
    char *dev;
    while ((dev = dict_for_each(&type->st_current_dict, &j)) != NULL) {
      struct stats *stats = key_to_stats(dev);

      sf_printf(sf, "%s %s", type->st_name, stats->s_dev);
      size_t k;
      for (k = 0; k < type->st_schema.sc_len; k++)
	{
	  sf_printf(sf, " %llu", stats->s_val[k]);
	}
      sf_printf(sf, "\n");
    }
  }

  rc = send(sf);

  free(sf->sf_path);
  free(sf->sf_mark);
  free(sf->sf_data);

  memset(sf, 0, sizeof(*sf));

  return rc;
}
