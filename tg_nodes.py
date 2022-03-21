#!/usr/bin/python3
__author__ = 'ArkJzzz (arkjzzz@gmail.com)'


import os
import datetime
import logging
import pandas
import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import ConversationHandler
from dotenv import load_dotenv


logging.basicConfig(
    format='%(asctime)s %(name)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%b-%d %H:%M:%S (%Z)',
)
logger = logging.getLogger('tg_nodes')


WAITING_MESSAGE, WAITING_FILE = range(2)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODES_FILE = os.path.join(BASE_DIR, 'nodes_file.xlsx')

ADVERTISING_IMAGE = 'advertising_image.jpeg'


def start(update, context):
    chat_id = update.effective_chat.id
    first_name = update.effective_chat.first_name

    welcome_message = f'Здравствуйте {first_name}!\n'\
        'Для получения информации по узлу '\
        'отправьте название улицы (можно не полностью, регистр не важен).'

    context.bot.send_message(chat_id, welcome_message)

    logger.info('start_handler: {}'.format(update.effective_chat.username))

    return WAITING_MESSAGE


def send_text_message(update, context):
    logger.debug('Новое сообщение:')

    chat_id = update.effective_chat.id
    username = update.effective_chat.username
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
            node = df.loc[df['АДРЕС'] == matched_address]
            answer = get_node_to_print(node)
            context.bot.send_message(chat_id, answer)
            logger.debug('Ответ: {}\n'.format(answer))

    days_to_ny(update, context)

    # advertising_message(update, context)

    return WAITING_MESSAGE


def get_dataframe(nodes_file):
    dataframe = pandas.read_excel(nodes_file, sheet_name='НОВАЯ БАЗА')
    addresses = dataframe['АДРЕС'].tolist()
    print('Всего строк в базе: {}'.format(dataframe.shape[0]))

    for address in addresses:
        dataframe = dataframe.replace(
            to_replace=address,
            value=str(address).upper()
        )

    return dataframe


def get_matched_addresses(df, input_phrase):
    addresses = df['АДРЕС'].tolist()

    matched_addresses = []
    for address in addresses:
        if input_phrase in address:
            matched_addresses.append(address)
    return matched_addresses


def get_node_to_print(node):
    node_values = node.values[0]
    node_to_print = (
        'Адрес: {}\n'
        'ID узла: {}\n'
        'Принадлежность: {}\n'
        'Тип: {}\n'
        'Допуск: {}\n'
        'Список: {}\n'
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
            node_values[8],
        )
    )

    return node_to_print


def update_nodes_file(update, context):
    chat_id = update.effective_chat.id
    waiting_answer = 'ожидаю файл'
    context.bot.send_message(chat_id, waiting_answer)

    return WAITING_FILE


def save_document(update, context):
    logger.debug('save_document')
    chat_id = update.effective_chat.id
    new_nodes_file = update.message.effective_attachment.get_file()
    new_nodes_file.download('nodes_file.xlsx')
    save_document_answer = 'файл загружен'
    context.bot.send_message(chat_id, save_document_answer)

    return WAITING_MESSAGE


def need_restart(update, context):
    chat_id = update.effective_chat.id
    waiting_answer = 'Необходимо перезапустить бота.\nОтправьте /start'
    context.bot.send_message(chat_id, waiting_answer)


def days_to_ny(update, context):
    chat_id = update.effective_chat.id

    now = datetime.datetime.now()
    then = datetime.datetime(now.year, 12, 31)
    delta = then - now

    if delta.days + 1 in [2, 3, 4]:
        day_improvise = 'дня'
    elif delta.days + 1 == 1:
        day_improvise = 'день'
    else:
        day_improvise = 'дней'

    days_to_ny_message = 'До Новго Года 🎄🍾🥂🎅 '\
        f'осталось потерпеть {delta.days + 1} {day_improvise} ⏰'

    if delta.days < 32:
        context.bot.send_message(chat_id, days_to_ny_message)

    return WAITING_MESSAGE


# Не удалять, использовать это для выгрузки фоток узлов
def advertising_message(update, context):
    chat_id = update.effective_chat.id

    with open(ADVERTISING_IMAGE, 'rb') as ad_image:
        context.bot.send_photo(
            chat_id=chat_id,
            photo=ad_image,
        )
    return WAITING_MESSAGE


def main():
    logger.setLevel(logging.DEBUG)

    load_dotenv()
    telegram_token = os.getenv("DEV_TELEGRAM_TOKEN")
    # telegram_token = os.getenv("TELEGRAM_TOKEN")

    updater = Updater(
        token=telegram_token,
        use_context=True,
    )

    mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    # do
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
        ],
        states={
            WAITING_MESSAGE: [
                MessageHandler(Filters.text, send_text_message),
                CommandHandler('update_nodes_file', update_nodes_file),
            ],
            WAITING_FILE: [
                MessageHandler(
                    Filters.document.mime_type(mime_type),
                    save_document
                )
            ]
        },
        fallbacks=[]
    )
    updater.dispatcher.add_handler(conv_handler)

    need_restart_handler = MessageHandler(Filters.text, need_restart)
    updater.dispatcher.add_handler(need_restart_handler)

    logger.debug('Используется файл с БД: {}'.format(NODES_FILE))

    try:
        logger.debug('Запускаем бота')
        updater.start_polling()

    except telegram.error.NetworkError:
        logger.error('Не могу подключиться к telegram')
    except Exception as err:
        logger.error('Бот упал с ошибкой:')
        logger.error(err)
        logger.debug(err, exc_info=True)

    updater.idle()
    logger.info('Бот остановлен')


if __name__ == "__main__":
    main()
