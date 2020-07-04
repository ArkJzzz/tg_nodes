#!/usr/bin/python3
__author__ = 'ArkJzzz (arkjzzz@gmail.com)'



import requests
import os
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler
import pandas
import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from dotenv import load_dotenv

logging.basicConfig(
        format='%(asctime)s %(name)s - %(funcName)s:%(lineno)d - %(message)s', 
        datefmt='%Y-%b-%d %H:%M:%S (%Z)',
    )
logger = logging.getLogger('tg_nodes')


NODES_FILE = 'nodes_file.xlsx'

def start(update, context):
    chat_id=update.effective_chat.id
    text='Здравствуйте!\nДля получения информации по узлу \
        отправьте название улицы (можно не полностью, регистр не важен).'

    context.bot.send_message(chat_id, text)

    logger.debug('start_handler: {}'.format(update.effective_chat.username))


def send_text_message(update, context):
    logger.debug('Новое сообщение:')

    chat_id = update.effective_chat.id
    username = update.effective_chat.username
    language_code = 'ru-RU'
    text = update.message.text
    text = text.upper()

    logger.debug('От {}, chat_id {}'.format(username, chat_id))
    logger.debug('Текст: {}'.format(text))

    df = get_dataframe(NODES_FILE)
    matched_addresses = get_matched_addresses(df, text)
    logger.debug('Совпавшие адреса: {}'.format(matched_addresses))

    if not matched_addresses:
        context.bot.send_message(chat_id, 'Совпадения не найдены')
        logger.debug('Ответ: Совпадения не найдены\n')
    else: 
        for matched_address in matched_addresses:
            node = df.loc[df['Адрес'] == matched_address]
            answer = get_node_to_print(node)
            context.bot.send_message(chat_id, answer)
            logger.debug('Ответ: {}\n'.format(answer))


def get_dataframe(nodes_file):
    dataframe = pandas.read_excel(nodes_file, sheet_name='БАЗА УЗЛОВ')
    addresses = dataframe['Адрес'].tolist()
    print('Всего строк в базе: {}'.format(dataframe.shape[0]))

    for address in addresses:
        dataframe = dataframe.replace(
            to_replace=address, 
            value=str(address).upper()
        )   

    return dataframe


def get_matched_addresses(df, input_phrase):
    addresses = df['Адрес'].tolist()

    matched_addresses = []
    for address in addresses:
        if input_phrase in address:
            matched_addresses.append(address)
    return matched_addresses


def get_node_to_print(node):
    node_values = node.values[0]
    node_to_print = (   
        'Адрес: {}\n'
        'Принадлежность: {}\n'
        'Тип: {}\n'
        'Район: {}\n'
        'Допуск: {}\n'
        'Размещение: \n{}\n'
        'Контакты: \n{}\n'
        'Примечания: \n{}\n'
        .format(
            node_values[0],
            node_values[1],
            node_values[2],
            node_values[3],
            node_values[4],
            node_values[5],
            node_values[6],
            node_values[7],
        )
    )

    return node_to_print


def main():
    logger.setLevel(logging.DEBUG)

    load_dotenv()
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    
    updater = Updater(
        token=telegram_token,
        use_context=True, 
        #request_kwargs=REQUEST_KWARGS,
    )


    # do

    start_handler = CommandHandler('start', start)
    updater.dispatcher.add_handler(start_handler)

    text_massage_handler = MessageHandler(Filters.text, send_text_message)
    updater.dispatcher.add_handler(text_massage_handler)

    logger.debug('Используется файл с БД: {}'.format(NODES_FILE))

    try:
        logger.debug('Запускаем бота')
        updater.start_polling()

    except telegram.error.NetworkError:
        logger.error('Не могу подключиться к telegram')
    except Exception  as err:
        logger.error('Бот упал с ошибкой:')
        logger.error(err)
        logger.debug(err, exc_info=True)

    updater.idle()
    logger.info('Бот остановлен') 

if __name__ == "__main__":
    main()