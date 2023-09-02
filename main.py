import json
import threading

import pika

from constatns.Constants import dl, jobs_collection
from server.ServerManager import ServerManager


def start_rabbit_mq_listener(servers_manager: ServerManager):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='JOBS')
    # channel.queue_declare(queue='SERVERS')

    def callback(ch, method, properties, body):
        if method.routing_key == "JOBS":
            jsons_configuration = json.loads(body)
            jsons_number = len(jsons_configuration)
            dl.logger.info(f"JOBS FROM RABBITMQ --> {jsons_number}  configuration : {jsons_configuration}")
            if jsons_number != 0:
                if len(servers_manager.servers) != 0:
                    if jsons_number > 1:
                        for json_conf in jsons_configuration:
                            servers_manager.start_job(json_conf)
                    else:
                        servers_manager.start_job(jsons_configuration[0])
                else:
                    dl.logger.error("Doesn't have any server yet")

    channel.basic_consume(queue='JOBS', on_message_callback=callback, auto_ack=True)
    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


def start_rabbit_mq_listener_for_servers(servers_manager):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    # channel.queue_declare(queue='JOBS')
    channel.queue_declare(queue='SERVERS')

    def callback(ch, method, properties, body):
        if method.routing_key == "SERVERS":
            jsons_configuration = json.loads(body)
            jsons_number = len(jsons_configuration)
            dl.logger.info(f"SERVERS FROM RABBITMQ --> {jsons_number}  SERVERS : {jsons_configuration}")
            if jsons_number != 0:
                if jsons_number > 1:
                    for json_conf in jsons_configuration:
                        servers_manager.add_server(json_conf)
                else:
                    servers_manager.add_server(jsons_configuration[0])

    channel.basic_consume(queue='SERVERS', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


if __name__ == '__main__':
    dl.logger.info('The program has been started ...')
    jobs_collection.clean()
    servers_manager = ServerManager()
    thr1 = threading.Thread(target=start_rabbit_mq_listener, args=(servers_manager,))
    thr = threading.Thread(target=start_rabbit_mq_listener_for_servers, args=(servers_manager,))
    thr.start()
    thr1.start()

