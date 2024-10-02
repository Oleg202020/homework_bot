import logging
import os
import requests
import time

from http import HTTPStatus
from logging import StreamHandler
from telebot import TeleBot

from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('SECRET_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = os.getenv('ENDPOINT')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='homwork_bot.log',
    filemode='w',
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения, необходимые для работы."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    logging.critical('Отсутствие обязательных переменных окружения.')
    raise ValueError


def send_message(bot, message):
    """
    Отправляет сообщение в Telegram, определяемый переменной TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса TeleBot и
    строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Отправлено сообщение: {message}')
    except Exception as error:
        message = f'Сообщение не отправлено: {error}'
        logger.error(message)


def get_api_answer(timestamp):
    """
    делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передаётся временная метка.
    В случае успешного запроса должна вернуть ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    try:
        payload = {'from_date': timestamp}
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            logger.error('Сервер не отвечает')
            raise AssertionError('Сервер не отвечает')
        return homework_statuses.json()
    except requests.RequestException as error:
        logger.error(error)


def check_response(response):
    """
    Проверяет ответ API на соответствие документации из урока.
    «API сервиса Практикум Домашка».
    """
    if not isinstance(response, dict):
        logger.error('Ответ сервера не содержит словарь')
        raise TypeError('Ответ сервера не содержит словарь')
    if 'homeworks' not in response:
        logger.error('Нет ключа homeworks')
        raise KeyError('Нет ключа homeworks')
    homeworks_response = response['homeworks']
    current_date_response = response['current_date']
    if not isinstance(homeworks_response, list):
        logger.error('Ответ сервера не содержит списк')
        raise TypeError('Ответ сервера не содержит списк')
    if homeworks_response is None:
        logger.error('Нет значение ключа homeworks')
        raise KeyError('Нет значение ключа homeworks')
    if current_date_response is None:
        logger.error('Нет значение ключа current_date')
        raise KeyError('Нет значение ключа current_date')
    return homeworks_response


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_VERDICTS.
    """
    homework_name = homework.get('homework_name')
    status_homework = homework.get('status')
    if homework_name is None:
        message = 'Пустое значение ключа.'
        logger.error(message)
        raise KeyError(message)
    if status_homework not in HOMEWORK_VERDICTS:
        message = 'Неизвестный ключ статуса домашней работы.'
        logger.error(message)
        raise KeyError(message)
    verdict = HOMEWORK_VERDICTS.get(status_homework)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """
    Основная логика работы бота.
    1 Сделать запрос к API.
    2 Проверить ответ.
    3 Если есть обновления — получить статус работы из обновления и отправить
    сообщение в Telegram.
    4 Подождать некоторое время и вернуться в пункт 1.
    """
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            check_response(response)
            if homework:
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                logger.debug('Нет новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
