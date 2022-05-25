"""metric.py"""
from typing import Text
import pika
import json
import numpy as np
from sklearn.metrics import mean_squared_log_error
from math import sqrt

# Cервис metric.py читает очереди y_true и y_pred с истинными ответами и предсказаниями.

try:
    # Подключимся к серверу:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    #connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    # Создадим очереди, с которыми будем работать:
    channel.queue_declare(queue='y_true')
    channel.queue_declare(queue='y_pred')

    data_true, data_pred = dict(), dict()
    rmse_y_true, rmse_y_pred = list(), list()
    
    def print_values(text):
        # Функция выводит текст в stdout и сохраняет в файл
        file_path = './logs/labels_log.txt'
        with open(file_path, 'a') as file:
            print(text)
            file.write(text + '\n')

    def callback(ch, method, properties, body):
        # Функция определяет, как работать с полученным сообщением:
        id = json.loads(body)['id']
        data = json.loads(body)['data']
        print_values(f'{id}:  Из очереди {method.routing_key} получено значение {data}')
        prepare_data(method.routing_key, id, data)
 
    def prepare_data(key, id, value):
        # Функция определяет, есть ли парное сообщение. 
        # Есть ли есть, то производим расчет метрики. Если нет, тогда сохраняем в буфер
        if key == 'y_true':
            if id in data_pred.keys():
                calc_rmsle(id=id, y_true=value, y_pred=data_pred.pop(id))
            else:
                data_true[id] = value
        elif key == 'y_pred':
            if id in data_true.keys():
                calc_rmsle(id=id, y_true=data_true.pop(id), y_pred=value)
            else:
                data_pred[id] = value

    def calc_rmsle(id, y_true, y_pred):
        # Функция сохраняет парные значения в отдельные списки, 
        # производит расчет метрики и пишет результат в файл
        try:
            rmse_y_true.append(y_true)
            rmse_y_pred.append(y_pred)
            print_values(f'{id}:  Есть оба значения y_true={rmse_y_true[-1]} y_pred={rmse_y_pred[-1]}')

            RMSE = sqrt(mean_squared_log_error(np.array(rmse_y_true), np.array(rmse_y_pred)))
            print_values(f'{id}:  RMSE = {RMSE:.5f}')

        except Exception as ex:
            print(ex)

        
    # Зададим правила чтения из очереди, указанной в параметре queue:
    # on_message_callback показывает какую функцию вызвать при получении сообщения
    channel.basic_consume(queue='y_true', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='y_pred', on_message_callback=callback, auto_ack=True)
    print('...Ожидание сообщений, для выхода нажмите CTRL+C')

    #Запустим чтение очереди. Скрипт будет работать до принудительной остановки: так мы не пропустим ни одного сообщения.
    channel.start_consuming()

except Exception as ex:
    print('Не удалось подключиться к очереди', ex)