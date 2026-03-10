# URL Shortener Service

Простой сервис сокращения ссылок на FastAPI с авторизацией и статистикой.

## Описание API

### Auth

- **POST /auth/register** — регистрация нового пользователя  
  Тело: `{ "email": "string", "password": "string" }`

- **POST /auth/login** — получение JWT-токена  
  Тело: `username=string&password=string` (form-urlencoded)

- **GET /auth/me** — информация о текущем пользователе (id, email)  
  Требуется авторизация (Bearer Token)

### Links

- **POST /links/shorten** — создание короткой ссылки  
  Тело: `{ "original_url": "string", "custom_alias": "string" (опционально), "expires_at": "string" (ISO, опционально) }`  
  Требуется авторизация (Bearer Token) для сохранения владельца

- **GET /{short_code}** — перенаправление на оригинальный URL  
  Если ссылка истекла — автоматически удаляется из базы

- **GET /links/{short_code}/stats** — статистика по ссылке  
  Возвращает: original_url, created_at, clicks, last_clicked, expires_at  
  Только для владельца (проверка owner_id)

- **PUT /links/{short_code}** — обновление ссылки  
  Тело: `{ "original_url": "string" (опционально), "expires_at": "string" (опционально) }`  
  Только для владельца

- **DELETE /links/{short_code}** — удаление своей ссылки  
  Только для владельца

- **DELETE /links/cleanup** — массовое удаление истёкших или неактивных ссылок  
  Параметры: `?mode=expired` или `?mode=inactive&inactive_days=30`  
  Только для авторизованного пользователя (удаляются только его ссылки)

## Примеры запросов

1. **Регистрация**
```bash
   curl -X POST "http://127.0.0.1:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "pass123"}'
```
2. **Логин**
```bash
   Bashcurl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=pass123"
```
3. **Создание ссылки**
```bash
  curl -X POST "http://127.0.0.1:8000/links/shorten" \
  -H "Authorization: Bearer <токен>" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://yandex.ru", "custom_alias": "yandex", "expires_at": "2026-12-31T23:59:59"}'
```
4. **Переход по ссылке**
Откройте в браузере (Пример):
http://127.0.0.1:8000/yandex
5. **Статистика**
```bash
curl -X GET "http://127.0.0.1:8000/links/yandex/stats" \ -H "Authorization: Bearer <токен>"
```
6. **Удаление истёкших ссылок**
```bash
curl -X DELETE "http://127.0.0.1:8000/links/cleanup?mode=expired" \ -H "Authorization: Bearer <токен>"
```

## Инструкция по запуску
```bash
1. Клонируйте репозиторий:Bashgit clone https://github.com/твой-username/url-shortener.git
2. cd url-shortener
3. Установите зависимости:pip install -r requirements.txt
4. Запустите PostgreSQL и Redis (через Docker):docker compose up -d db redis
5. Запустите сервер:uvicorn app.main:app --reload

Проверка осуществляется в документации!!!

Swagger-документация: http://127.0.0.1:8000/docs
```

## Описание БД
```bash
Используется PostgreSQL.
Таблицы:

1. users
id (integer, primary key)
email (string, unique)
hashed_password (string)
is_active (boolean, default true)

2. links
id (integer, primary key)
short_code (string, unique)
original_url (string)
custom_alias (string, unique, nullable)
created_at (timestamp)
expires_at (timestamp, nullable)
clicks (integer, default 0)
last_clicked (timestamp, nullable)
owner_id (integer, foreign key → users.id, nullable)


Кэширование (Redis) применяется к original_url и статистике для ускорения редиректа и получения stats.