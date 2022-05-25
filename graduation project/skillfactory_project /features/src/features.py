"""features.py"""
import pika
import numpy as np
import pandas as pd
import json
import time
from datetime import datetime

# Cервис для отправки признаков в одну очередь, а истинных ответов — в другую.

VERSION = 'v01'
LOAD_DATA_PATH = f'./sber_housing_market_data_{VERSION}.csv'

df = pd.read_csv(LOAD_DATA_PATH)
cat_cols = [
    'sub_area',
    'ecology',
    'child_on_acc_pre_school',
    'modern_education_share',
    'old_education_build_share',
    'metro_id_and_min_walk',
    'sub_area_and_metro_min_walk'
]
for column in cat_cols:
    df[column] = df[column].astype(str)

X = df.drop(columns=['price_doc_sqm'])
y = df['price_doc_sqm']

class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


while True:
    try:
        random_row = np.random.randint(0, X.shape[0]-1)

        # Подключение к серверу на локальном хосте:
        # Если вы захотите подключиться к удаленному серверу, то вместо localhost укажите его IP-адрес.
        connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        #connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        # Создадим очередь, с которой будем работать:
        channel.queue_declare(queue='y_true')
        channel.queue_declare(queue='Features')

        # Подготовим сообщение в виде словаря, который будет отправлен в виде json
        now = datetime.now().strftime('%Y%m%d%H%M%S')

        data_y = {'id': now, 'data': y[random_row]}
        serialized_data_y = json.dumps(data_y, cls=NumpyEncoder)

        data_x = {'id': now, 'data': list(X.loc[random_row])}
        serialized_data_x = json.dumps(data_x, cls=NumpyEncoder)

        # Опубликуем сообщение
        # exchange определяет, в какую очередь отправляется сообщение. Если мы используем дефолтную точку обмена, то значение можно оставить пустым.
        # параметр routing_key указывает имя очереди, 
        # параметр body тело самого сообщения, 
        channel.basic_publish(exchange='', routing_key='y_true', body=serialized_data_y)
        print('Сообщение с правильным ответом, отправлено в очередь y_true')

        # Опубликуем сообщение в очередь Features
        channel.basic_publish(exchange='', routing_key='Features', body=serialized_data_x)
        print('Сообщение с набором признаков, отправлено в очередь Features')

        # Закроем подключение 
        connection.close()
        time.sleep(2)
    except Exception as ex:
        print('Не удалось подключиться к очереди', ex)