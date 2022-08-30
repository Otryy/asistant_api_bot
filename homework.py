import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import EmptyList, ErrorMesage, NotList, NotTwoHundred

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format=(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(lineno)d'
    ),
    level=logging.DEBUG,
    filename='asistant_bot.log',
    encoding='utf-8')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info('Начинаем отправку сообщения.')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f'{message}'
        )
        
    except ErrorMesage as error:
        raise ErrorMesage(error)

    else:
        logging.info('Отправка сообщения прошла успешно!.')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    logging.info('Начинаем запрос к API.')
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )

    except NotTwoHundred as error:
        message_error = f'{error}'
        logging.error(message_error)

    response = requests.get(
        url=ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if response.status_code != HTTPStatus.OK:
        raise Exception('Ошибка ответа от API.')

    logging.info('Ответ от API получен!.')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info('Начинаем проверку корректности ответа API.')
    if not isinstance(response, dict):
        raise TypeError('Вернулся не словарь')

    if 'homeworks' not in response:
        raise EmptyList('Пришел пустой ответ')

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise NotList('Вернулся не список')

    logging.info('Ответ API пришел в нужном формате!.')
    return homeworks


def parse_status(homework):
    """Извлекает из ответа API статус домашней работы."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        message_error = 'Пустое значение homework_name'
        raise KeyError(message_error)
    homework_status = homework.get('status')

    if 'status' not in homework:
        message_error = 'Пустое значение status'
        raise KeyError(message_error)

    if homework_status not in HOMEWORK_STATUSES:
        message_error = 'Пустое значение homework_status'
        raise KeyError(message_error)

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = ('Отсутствуют обязательные переменные окружения!')
        logging.critical(message)
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    start_message = 'Стартуем©'
    send_message(bot, start_message)
    current_timestamp = int(time.time())
    default_status = ''
    old_error = ''
    homework_status = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework_status = homeworks[0].get('status')
                if default_status != homework_status:
                    homework_status = default_status
                    message = parse_status(homeworks[0])
                else:
                    info = 'Пришел пустой список домашки'
                    logging.debug(info)
                    message = 'Тут тоже нет домашек'

                send_message(bot, message)
            else:
                info = f'Статус не изменился, ждем ещё {RETRY_TIME}'
                logging.debug(info)

        except Exception as error:
            message_error = f'Сбой в работе программы: {error}'
            logging.error(message_error)
            if message_error != old_error:
                send_message(bot, message_error)
                old_error = message_error
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
