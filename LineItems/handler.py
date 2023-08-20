import datetime
from datetime import timedelta
import json
import os
import requests
import boto3
import logging
import time


def get_refresh_token():
    refresh_token = os.environ['REFRESH_TOKEN']

    return refresh_token


def get_access_token():
    refresh_token = get_refresh_token()

    response = requests.post('https://drchrono.com/o/token/', data={
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'client_id': os.environ['CLIENT_ID'],
        'client_secret': os.environ['CLIENT_SECRET'],
    })

    response.raise_for_status()
    data = response.json()
    access_token = data['access_token']
    # refresh_token = data['refresh_token']

    return access_token


def get_list(endpoint):
    try:
        time.sleep(10)
        access_token = get_access_token()
        s = requests.session()
        s.cookies.clear()
        response = s.get(endpoint, headers={
            'Authorization': 'Bearer %s' % access_token,
        }, timeout=50)
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            time.sleep(5)
            get_list(endpoint)
    except Exception as e:
        print('++++++++++++++++++++++++++++++++{}'.format(e))
        time.sleep(5)
        get_list(endpoint)


def put_line_items2table(data, table_name):
    DB = boto3.resource('dynamodb',
                        aws_access_key_id=os.environ['AWS_ID'],
                        aws_secret_access_key=os.environ['AWS_KEY'],
                        region_name=os.environ['REGION'])
    try:
        table = DB.create_table(
            TableName='line_items',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'posted_date',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'posted_date',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )

        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        logging.warning('Successfully created Table...')
    except Exception as err:
        logging.warning('Table: {} already exists'.format(table_name))

    table = DB.Table(table_name)

    list = data['results']

    for item in list:
        del_keys = []
        for key, value in item.items():
            if value is None:
                del_keys.append(key)
        for key in del_keys:
            del item[key]
        table.put_item(Item=item)


def save_line_item(endpoint):
    data = get_list(endpoint)
    table_name = 'line_items'
    put_line_items2table(data, table_name)
    endpoint_next = data['next']
    cnt = len(data['results'])
    print('{} line-items were saved. The next page is {}'.format(cnt, endpoint_next))
    if endpoint_next is not None:
        save_line_item(endpoint_next)


def line_items_by_yesterday(posted_date):
    endpoint = 'https://drchrono.com/api/line_items?posted_date={}'.format(posted_date)
    save_line_item(endpoint)


def line_items():
    endpoint = 'https://drchrono.com/api/line_items'
    save_line_item(endpoint)


def main():
    print('starting...')

    yesterday = (datetime.datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    line_items_by_yesterday(yesterday)


def handler(event, context):
    try:
        now = datetime.datetime.now()
        current_time = now.strftime("%d/%m/%Y %H:%M:%S")
        print("Started at =", current_time)

        main()

        now = datetime.datetime.now()
        current_time = now.strftime("%d/%m/%Y %H:%M:%S")
        print("Ended at =", current_time)
    except Exception as e:
        print(e)


if __name__ == "__main__":

    try:
        now = datetime.datetime.now()
        current_time = now.strftime("%d/%m/%Y %H:%M:%S")
        print("Current Time =", current_time)

        main()

        now = datetime.datetime.now()
        current_time = now.strftime("%d/%m/%Y %H:%M:%S")
        print("Current Time =", current_time)
    except Exception as e:
        print(e)
