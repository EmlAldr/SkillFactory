"""model.py"""
import pika
import pickle
import json
import numpy as np
from catboost import CatBoostRegressor


# Cервис прочитает признаки, сделает предсказание и отправит его в очередь.

VERSION = 'v01'
LOAD_MODEL_FULL_PATH_JSON = f'./sber_housing_market_model_{VERSION}.json'


def load_model(model_path, print_model_info=True): 
    # Загрузим модель
    model = CatBoostRegressor()
    model.load_model(model_path, format='json')
    
    model_type = model.get_metadata()['model_type']
    model_version = model.get_metadata()['model_version']
    print(f'Load {model_type} model version {model_version}')
    
    if print_model_info:
        model_description = model.get_metadata()['model_description']     
        print(model_description)
        
    return model


regressor = load_model(LOAD_MODEL_FULL_PATH_JSON)

try:
    # Подключимся к серверу:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    #connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    # Укажем, с какой очередью будем работать:
    channel.queue_declare(queue='Features')
    channel.queue_declare(queue='y_pred')

    # Напишем функцию, определяющую, как работать с полученным сообщением:
    def callback(ch, method, properties, body):
        # получим вектор признаковдля пресказания
        id = json.loads(body)['id']
        X_pred = json.loads(body)['data']
        print(f'{id}:  Получен вектор признаков {X_pred} ')

        # сделаем предсказание по модели и сериализуем
        y_red = np.exp(regressor.predict(X_pred)) - 1
        data_y = {'id': id, 'data': y_red}
        serialized_data_y = json.dumps(data_y)

        # отправим предсказанное значение
        channel.basic_publish(exchange='', routing_key='y_pred', body=serialized_data_y)
        print(f'{id}:  Сообщение с предсказанным ответом, отправлено в очередь y_pred')

    # Зададим правила чтения из очереди, указанной в параметре queue:
    # on_message_callback показывает какую функцию вызвать при получении сообщения
    channel.basic_consume(queue='Features', on_message_callback=callback, auto_ack=True)
    print('...Ожидание сообщений, для выхода нажмите CTRL+C')

    #Запустим чтение очереди. Скрипт будет работать до принудительной остановки: так мы не пропустим ни одного сообщения.
    channel.start_consuming()

except Exception as ex:
    print('Не удалось подключиться к очереди', ex)
