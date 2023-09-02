import json
import pika
if __name__ == '__main__':
    with open("jobs.json", 'r') as file:
        json_data = json.load(file)
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='JOBS')

    byte_array = json.dumps(json_data)
    channel.basic_publish(exchange='',
                          routing_key='JOBS',
                          body=byte_array)
    print(" [x] Sent 'Hello World!'")