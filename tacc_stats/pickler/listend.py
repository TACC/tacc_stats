#!/usr/bin/env python
import pika
import os, sys
import time

stats_dir = "/hpc/tacc_stats_site/ls5/archive"

def on_message(channel, method_frame, header_frame, body):
    if body[0] == '$': host = body.split('\n')[1].split()[1]       
    else: host = body.split()[2]

    print host
    host_dir = os.path.join(stats_dir, host)
    if not os.path.exists(host_dir):
        os.makedirs(host_dir)
    
    current_path = os.path.join(host_dir, "current")
    if body[0] == '$':
        if os.path.exists(current_path):
            os.unlink(current_path)

        with open(current_path, 'w') as fd:
            link_path = os.path.join(host_dir, str(int(time.time())))
            os.link(current_path, link_path)

    with open(current_path, 'a') as fd:
        fd.write(body)

    channel.basic_ack(delivery_tag=method_frame.delivery_tag)

connection = pika.BlockingConnection()
channel = connection.channel()
channel.basic_consume(on_message, 'ls5')
try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
connection.close()
