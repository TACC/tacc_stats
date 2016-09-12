#!/usr/bin/env python
import pika
import os, sys
import time
import tacc_stats.cfg as cfg

def on_message(channel, method_frame, header_frame, body):
    if body[0] == '$': host = body.split('\n')[1].split()[1]       
    else: host = body.split()[2]

    host_dir = os.path.join(cfg.archive_dir, host)
    if not os.path.exists(host_dir):
        os.makedirs(host_dir)
    
    current_path = os.path.join(host_dir, "current")
    if body[0] == '$':
        if os.path.exists(current_path):
            os.unlink(current_path)

        with open(current_path, 'w') as fd:
            link_path = os.path.join(host_dir, str(int(time.time())))
            if os.path.exists(link_path):
                os.remove(link_path)
            os.link(current_path, link_path)

    with open(current_path, 'a') as fd:
        fd.write(body)

    channel.basic_ack(delivery_tag=method_frame.delivery_tag)

parameters = pika.ConnectionParameters(cfg.rmq_server)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()
channel.basic_consume(on_message, cfg.rmq_queue)
try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
connection.close()
