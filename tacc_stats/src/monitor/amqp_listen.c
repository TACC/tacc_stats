/*
  Adapted from rabbitmq-c examples/amqp_listen.c 
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <getopt.h>
#include <stdint.h>
#include <amqp_tcp_socket.h>
#include <amqp.h>
#include <amqp_framing.h>

#include <assert.h>

#include "trace.h"

int main(int argc, char const *const *argv)
{
  const char *hostname = NULL;
  const char *port = NULL;
  int status;
  char const *exchange;
  char const *bindingkey;
  amqp_socket_t *socket = NULL;
  amqp_connection_state_t conn;

  amqp_bytes_t queuename;

  if (argc < 3) {
    fprintf(stderr, "Usage: amqp_listend -s SERVER -p PORT (5672 is default)\n");
    return 1;
  }

  struct option opts[] = {
    { "server", required_argument, 0, 's' },
    { "port", required_argument, 0, 'p' },
    { NULL, 0, 0, 0 },
  };

  int c;
  while ((c = getopt_long(argc, argv, "s:p:", opts, 0)) != -1) {
    switch (c) {
    case 's':
      hostname = optarg;
      continue;
    case 'p':
      port = optarg;
      continue;
    }
  }

  if (hostname == NULL) {
    FATAL("Must specify a RMQ server with -s [--server] argument.\n");
  }
  if (port == NULL) {
    port = "5672";
  }

  exchange = "amq.direct";
  bindingkey = "tacc_stats";

  conn = amqp_new_connection();
  socket = amqp_tcp_socket_new(conn);
  status = amqp_socket_open(socket, hostname, atoi(port));
  amqp_login(conn, "/", 0, 131072, 0, AMQP_SASL_METHOD_PLAIN, "guest", "guest");
  amqp_channel_open(conn, 1);
  amqp_get_rpc_reply(conn);

  {
    amqp_queue_declare_ok_t *r = amqp_queue_declare(conn, 1, amqp_empty_bytes, 0, 0, 0, 1,
                                 amqp_empty_table);
    amqp_get_rpc_reply(conn);
    queuename = amqp_bytes_malloc_dup(r->queue);
    if (queuename.bytes == NULL) {
      fprintf(stderr, "Out of memory while copying queue name");
      return 1;
    }
  }

  amqp_queue_bind(conn, 1, queuename, amqp_cstring_bytes(exchange), amqp_cstring_bytes(bindingkey),
                  amqp_empty_table);
  amqp_get_rpc_reply(conn);

  amqp_basic_consume(conn, 1, queuename, amqp_empty_bytes, 0, 1, 0, amqp_empty_table);
  amqp_get_rpc_reply(conn);

  {
    while (1) {
      amqp_rpc_reply_t res;
      amqp_envelope_t envelope;

      amqp_maybe_release_buffers(conn);

      res = amqp_consume_message(conn, &envelope, NULL, 0);

      if (AMQP_RESPONSE_NORMAL != res.reply_type) {
        break;
      }
      /*
      printf("Delivery %u, exchange %.*s routingkey %.*s\n",
             (unsigned) envelope.delivery_tag,
             (int) envelope.exchange.len, (char *) envelope.exchange.bytes,
             (int) envelope.routing_key.len, (char *) envelope.routing_key.bytes);

      if (envelope.message.properties._flags & AMQP_BASIC_CONTENT_TYPE_FLAG) {
        printf("Content-type: %.*s\n",
               (int) envelope.message.properties.content_type.len,
               (char *) envelope.message.properties.content_type.bytes);
      }
      */
      printf("%.*s\n", (int) envelope.message.body.len, (char *) envelope.message.body.bytes);
      amqp_destroy_envelope(&envelope);
    }
  }

  amqp_channel_close(conn, 1, AMQP_REPLY_SUCCESS);
  amqp_connection_close(conn, AMQP_REPLY_SUCCESS);
  amqp_destroy_connection(conn);

  return 0;
}
