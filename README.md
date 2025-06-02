# Homework Bot

Бот для Telegram, который раз в 10 минут опрашивает API сервиса **&laquo;Яндекс Практикум. Домашка&raquo;** и присылает в чат обновления о статусе проверки ваших работ.

---

## Содержание
1. [Как это работает](#как-это-работает)
2. [Технологии и зависимости](#технологии-и-зависимости)
3. [Переменные окружения](#переменные-окружения)
4. [Установка и запуск локально](#установка-и-запуск-локально)
5. [Деплой на сервер](#деплой-на-сервер)
6. [Логи и отладка](#логи-и-отладка)
7. [Обработка ошибок](#обработка-ошибок)
8. [Структура проекта](#структура-проекта)
9. [Контакты](#контакты)

---

## Как это работает

1. **Запрос к API**  
   Каждые `RETRY_PERIOD` секунд (по умолчанию — 600 с) бот делает запрос к `ENDPOINT`, передавая метку времени `from_date`.

2. **Проверка ответа**  
   - Код ответа должен быть `200 OK`.  
   - Ответ — JSON со списком домашних работ `homeworks`.  

3. **Формирование сообщения**  
   Для первой (самой свежей) работы из списка вызывается `parse_status()`, которая превращает статус в человекочитаемый текст на основе словаря `HOMEWORK_VERDICTS`.

4. **Отправка в Telegram**  
   Сообщение уходит в чат с ID, указанным в `TELEGRAM_CHAT_ID`. Чтобы не спамить, бот запоминает последнее отправленное сообщение и шлёт новое только если текст изменился.

---

## Технологии и зависимости

| Пакет      | Версия | Назначение                |
|------------|--------|---------------------------|
| Python     | 3.10+  | Язык программирования     |
| `python-telegram-bot` \| `pyTelegramBotAPI` | ^4.15 | Работа с Telegram Bot API |
| `requests` | ^2.31  | HTTP-запросы к API        |
| `python-dotenv` | ^1.0 | Работа с `.env`-файлом   |
| `logging`  | stdlib | Логирование               |

Список фиксирован в `requirements.txt`.

---

## Переменные окружения

Создайте файл `.env` в корне проекта и добавьте в него:

```dotenv
# Токен Яндекс.Практикум
SECRET_TOKEN=your_practicum_token

# Токен вашего Telegram-бота
TELEGRAM_TOKEN=your_telegram_bot_token

# ID чата (группа/личный), куда бот будет слать сообщения
CHAT_ID=123456789

# URL эндпоинта Практикума
ENDPOINT=https://practicum.yandex.ru/api/user_api/homework_statuses/
```

* *"Важно: никогда не коммитьте '.env' в публичный репозиторий."*


## Установка и запуск локально

```bash
# 1. Клонируем репозиторий
git clone git@github.com:Oleg202020/homework_bot.git
cd homework_bot

# 2. Создаём виртуальное окружение и активируем
python -m venv venv
source venv/bin/activate  # для Windows: venv\Scripts\activate

# 3. Ставим зависимости
pip install -r requirements.txt

# 4. Создаём .env и заполняем переменные (см. выше)

# 5. Запускаем
python bot.py          # или python -m homework_bot
```
Бот начнёт работать в консоли. Чтобы остановить — 'Ctrl+C'.


## Деплой на сервер

На Linux-сервере (Ubuntu 22.04+):
   * 1 Скопируйте файлы и .env на сервер (scp или Git).
   * 2 Установите Python 3.10+ и systemd-службу, напр.:
```ini
# /etc/systemd/system/homework_bot.service
[Unit]
Description=Homework Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/homework_bot
EnvironmentFile=/home/ubuntu/homework_bot/.env
ExecStart=/usr/bin/python /home/ubuntu/homework_bot/homework.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
   * 3 Перезапустите службу и добавьте в автозапуск:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now homework_bot
```

## Логи и отладка
   * Формат лога: '2025-06-02 12:34:56,789 INFO <сообщение> <функция> <строка>'.

   * По умолчанию логи выводятся в 'stdout'.
   Перенаправьте их в файл, указав переменную окружения 'PYTHONUNBUFFERED=1' и используя перенаправление оболочки:
```
python homework.py >> homework_bot.log 2>&1
```

## Обработка ошибок
|Исключение  |	Когда возникает	  |  Действие бота     |
|------------|--------------------|--------------------|
|ValueError	 |Отсутствует хотя бы одна переменная окружения	| Завершает работу (critical)
|ConnectionError	| Проблемы с сетью/доступностью API	| Пишет ошибку в логи, повторяет запрос
| ResponseStatusError	| API вернул статус ≠ 200	| Отчитывается в логи, отправляет в чат
| telebot.apihelper.*	|Ошибки Telegram-API	| Лог + ожидание + следующая попытка
|Любой Exception	| Непредвиденная ошибка в цикле	| Шлёт сообщение в Telegram о сбое

## Структура проекта
```text
homework_bot/
├── homework.py         # главный скрипт (main)
├── exception.py        # кастомные исключения
├── requirements.txt    # список зависимостей
├── .env.example        # пример env-файла
└── README.md
```

## Контакты

* Автор: Larionov Oleg
* E-mail: jktu2005@yandex.ru
* GitHub: @Oleg202020