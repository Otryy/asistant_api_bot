import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import EmptyList, NotList, NotTwoHundred

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='asistant_bot.log',
    encoding='utf-8')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=f'{message}'
    )


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code != 200:
            raise Exception
        else:
            return response.json()

    except NotTwoHundred as error:
        mess = f'{error}'
        logging.error(mess)


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info('Начинаем проверку корректности ответа API.')
    if not isinstance(response, dict):
        raise TypeError('Не словарь')

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise NotList('Не список')

    if 'homeworks' not in response:
        raise EmptyList(f'Пришел пустой ответ: {response}')
    logging.info('Ответ API пришел в нужном формате!.')
    return homeworks


def parse_status(homework):
    """Извлекает из ответа API статус домашней работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except TypeError as error:
        mess = f'Ошибка {error} в получении информации, Список работ пуст'
        logging.error(mess)
        return mess


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_CHAT_ID and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    day = 43200
    current_timestamp = 1660676115 - day * 30
    while True:
        try:
            response = get_api_answer(current_timestamp=current_timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            send_message(bot, message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot.send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
