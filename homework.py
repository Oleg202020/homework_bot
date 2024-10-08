import logging
import os
import sys
import time
from contextlib import suppress
from http import HTTPStatus

import requests
import telebot
from dotenv import load_dotenv
from telebot import TeleBot

from exception import ResponseStatusError

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

logger = logging.getLogger(__name__)
format = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s %(funcName)s %(lineno)d'
)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
handler.setFormatter(format)


def check_tokens():
    """Проверяет доступность переменных окружения, необходимые для работы."""
    tokens = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    missing_tokens = []
    missing_tokens = [missing_tokens for name in tokens if not globals()[name]]
    if missing_tokens:
        message = (
            f'Отсутствует обязательная переменная окружения{missing_tokens}'
        )
        logger.critical(message)
        raise ValueError(message)
    logger.debug('Проверка переменных окружения пройдена')


def send_message(bot, message):
    """
    Отправляет сообщение в Telegram, определяемый переменной TELEGRAM_CHAT_ID.

    Принимает на вход два параметра: экземпляр класса TeleBot и
    строку с текстом сообщения.
    """
    logger.info('Начало отправки сообщения.')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.debug(f'Отправлено сообщение: {message}')


def get_api_answer(timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.

    В качестве параметра в функцию передаётся временная метка.
    В случае успешного запроса должна вернуть ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    try:
        payload = {'from_date': timestamp}
        logger.info('Начало отправки запроса к API')
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.RequestException as error:
        raise ConnectionError(
            f'Запрос был сделан к {ENDPOINT}.'
            f'Сбой при запросе к API: {error}'
            f'Параметры запроса{payload}'
        )
    if homework_statuses.status_code != HTTPStatus.OK:
        error_message = (
            f'Запрос был сделан к {ENDPOINT}. '
            f'Ошибка ответа API.Статус:{homework_statuses.status_code}. '
            f'Параметры запроса{payload}'
        )
        raise ResponseStatusError(error_message)
    logger.info('Успешное получение ответа API')
    return homework_statuses.json()


def check_response(response):
    """
    Проверяет ответ API на соответствие документации из урока.
    «API сервиса Практикум Домашка».
    """
    logger.info('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ сервера не содержит словарь,'
            f'вместо словаря был получен {type(response)}'
        )
    if 'homeworks' not in response:
        raise KeyError('В ответе сервера нет ключа  homeworks')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            'Ответ сервера не содержит списка, со значением ключа homeworks'
            f'вместо ожидаемого списка был найден тип данных {type(homeworks)}'
        )
    logger.info('Проверка ответа API пройдена')


def parse_status(homework):
    """
    Извлекает из информацию о конкретной домашней работе статус этой работы.

    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_VERDICTS.
    """
    logger.info('начало исполнения функции parse_status')
    if 'homework_name' not in homework:
        raise KeyError('В словаре homework нет ключа "homework_name"')
    homework_name = homework['homework_name']
    status_homework = homework['status']
    if status_homework not in HOMEWORK_VERDICTS:
        raise ValueError(
            'Недокументированное статуса для ключа домашней работы.'
        )
    verdict = HOMEWORK_VERDICTS.get(status_homework)
    logger.info('окончание исполнения функции parse_status')
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
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    old_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks_response = response['homeworks']
            if not homeworks_response:
                logger.debug('Нет новых статусов домашней работы')
                continue
            message = parse_status(homeworks_response[0])
            if old_message != message:
                send_message(bot, message)
                old_message = message
            else:
                logger.debug('Статус сообщения не изменился, повтор статуса')
            timestamp = response.get('current_date', timestamp)
        except (telebot.apihelper.ApiTelegramException,
                requests.RequestException
                ) as error:
            logger.debug(f'Ошибка сетевого подключения:{error}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(message)
            if old_message != message:
                with suppress(
                    telebot.apihelper.ApiTelegramException,
                    requests.RequestException
                ):
                    send_message(bot, message)
                    old_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
