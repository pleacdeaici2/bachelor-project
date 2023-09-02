
import json
import os

import pika

if __name__ == '__main__':
    with open("secondserver.json", 'r') as file:
        json_data = json.load(file)
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='SERVERS')

    byte_array = json.dumps(json_data)
    channel.basic_publish(exchange='',
                          routing_key='SERVERS',
                          body=byte_array)


    print(" [x] Sent 'Hello World!'")
