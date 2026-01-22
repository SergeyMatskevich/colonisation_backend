# Colonisation Backend

Backend сервис для игры Колонизаторы (Catan) на FastAPI и PostgreSQL.

## Технологии

- **FastAPI** - современный веб-фреймворк для Python
- **PostgreSQL** - реляционная база данных
- **SQLAlchemy** - ORM для работы с БД
- **Alembic** - миграции базы данных
- **Pydantic** - валидация данных

## Структура проекта

```
colonisation_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Точка входа приложения
│   ├── api/                    # API endpoints
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── games.py    # Эндпоинты для игр
│   │           └── users.py    # Эндпоинты для пользователей
│   ├── core/                   # Ядро приложения
│   │   ├── config.py           # Конфигурация
│   │   ├── database.py         # Настройка БД
│   │   └── security.py         # Функции безопасности
│   ├── models/                 # SQLAlchemy модели
│   │   ├── base.py
│   │   ├── user.py
│   │   └── game.py
│   └── schemas/                # Pydantic схемы
│       ├── user.py
│       └── game.py
├── alembic/                    # Миграции БД
├── requirements.txt            # Зависимости Python
├── docker-compose.yml          # Docker конфигурация для PostgreSQL
└── .env.example                # Пример файла с переменными окружения
```

## Установка и запуск

### Требования

- Python 3.10+
- PostgreSQL 15+ (или Docker)
- pip

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd colonisation_backend
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка базы данных

#### Вариант A: Использование Docker (рекомендуется)

```bash
docker-compose up -d
```

#### Вариант B: Локальная установка PostgreSQL

Создайте базу данных:
```bash
createdb catan_db
```

### 5. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Отредактируйте `.env` и установите правильные значения:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/catan_db
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### 6. Запуск миграций

```bash
alembic upgrade head
```

### 7. Запуск приложения

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Приложение будет доступно по адресу:
- API: http://localhost:8000
- Документация Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Документация API

FastAPI автоматически генерирует интерактивную документацию API. Есть несколько способов получить и поделиться документацией:

### 1. Интерактивная документация (Swagger UI)

После запуска приложения откройте в браузере:
```
http://localhost:8000/docs
```

Здесь вы можете:
- Просматривать все доступные эндпоинты
- Видеть схемы запросов и ответов
- Тестировать API прямо в браузере

### 2. Альтернативная документация (ReDoc)

Более читаемый формат документации:
```
http://localhost:8000/redoc
```

### 3. Экспорт OpenAPI схемы

Для использования документации в других проектах (например, для генерации клиентского кода), экспортируйте OpenAPI схему:

```bash
python export_api_docs.py
```

Это создаст файл `openapi.json` в корне проекта, который можно:
- Импортировать в Postman
- Использовать для генерации клиентского кода (например, через `openapi-generator`)
- Поделиться с другими разработчиками
- Использовать в других инструментах (Swagger Editor, Insomnia и т.д.)

### 4. Использование OpenAPI схемы в других проектах

#### Генерация клиентского кода (TypeScript/JavaScript)

```bash
npx @openapitools/openapi-generator-cli generate \
  -i openapi.json \
  -g typescript-axios \
  -o ./generated-client
```

#### Генерация клиентского кода (Python)

```bash
openapi-generator generate \
  -i openapi.json \
  -g python \
  -o ./generated-client
```

#### Импорт в Postman

1. Откройте Postman
2. Нажмите "Import"
3. Выберите файл `openapi.json`
4. Все эндпоинты будут импортированы с примерами запросов

#### Использование в Swagger Editor

1. Откройте https://editor.swagger.io/
2. File → Import File
3. Выберите `openapi.json`

## API Endpoints

### Пользователи

- `POST /api/v1/users/` - Создание нового пользователя
- `GET /api/v1/users/` - Получение списка пользователей
- `GET /api/v1/users/{user_id}` - Получение пользователя по ID

### Игры

- `POST /api/v1/games/` - Создание новой игры
- `GET /api/v1/games/` - Получение списка игр
- `GET /api/v1/games/{game_id}` - Получение игры по ID
- `PATCH /api/v1/games/{game_id}` - Обновление игры
- `POST /api/v1/games/{game_id}/players/{player_id}` - Добавление игрока в игру

## Разработка

### Создание миграций

```bash
alembic revision --autogenerate -m "описание изменений"
alembic upgrade head
```

### Тестирование

```bash
# Пример запроса для создания пользователя
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123"
  }'

# Создание игры
curl -X POST "http://localhost:8000/api/v1/games/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Game",
    "max_players": 4
  }'
```

## Планы на будущее

- [ ] Реализация игровой логики Catan
- [ ] WebSocket для реального времени
- [ ] Аутентификация и авторизация (JWT)
- [ ] Расширение правил из дополнений
- [ ] Система сохранений игр
- [ ] Статистика игроков
- [ ] Система рейтингов

## Лицензия

См. файл LICENSE
