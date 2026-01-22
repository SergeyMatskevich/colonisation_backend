# Документация API

## Быстрый старт

### Получение документации

1. **Интерактивная документация (Swagger UI)**
   - Запустите сервер: `python run.py` или `uvicorn app.main:app --reload`
   - Откройте в браузере: http://localhost:8000/docs

2. **Экспорт OpenAPI схемы**
   ```bash
   python export_api_docs.py
   ```
   Создаст файл `openapi.json` в корне проекта.

3. **Прямой доступ к OpenAPI JSON**
   - После запуска сервера: http://localhost:8000/openapi.json
   - Можно скачать напрямую из браузера

## Использование в других проектах

### 1. Импорт в Postman

1. Откройте Postman
2. Нажмите **Import** (кнопка в левом верхнем углу)
3. Выберите файл `openapi.json`
4. Все эндпоинты будут импортированы с примерами запросов

### 2. Генерация клиентского кода

#### TypeScript/JavaScript
```bash
npx @openapitools/openapi-generator-cli generate \
  -i openapi.json \
  -g typescript-axios \
  -o ./generated-client
```

#### Python
```bash
# Установите openapi-generator-cli
npm install -g @openapitools/openapi-generator-cli

# Генерация клиента
openapi-generator-cli generate \
  -i openapi.json \
  -g python \
  -o ./generated-client
```

#### C# / .NET
```bash
openapi-generator-cli generate \
  -i openapi.json \
  -g csharp \
  -o ./generated-client
```

### 3. Использование в Swagger Editor

1. Откройте https://editor.swagger.io/
2. **File** → **Import File**
3. Выберите `openapi.json`
4. Просматривайте и редактируйте документацию

### 4. Использование в Insomnia

1. Откройте Insomnia
2. **Application** → **Preferences** → **Data** → **Import Data**
3. Выберите **OpenAPI 3.0** и укажите путь к `openapi.json`

### 5. Интеграция с другими инструментами

- **Redoc**: Используйте `openapi.json` для генерации статической документации
- **Stoplight**: Импортируйте схему для создания документации
- **API Blueprint**: Конвертируйте через инструменты конвертации

## Обновление документации

При изменении API эндпоинтов:

1. Обновите код эндпоинтов
2. Запустите скрипт экспорта:
   ```bash
   python export_api_docs.py
   ```
3. Обновите файл `openapi.json` в репозитории (если он отслеживается в git)
4. Уведомите команду о изменениях

## Автоматическое обновление

Можно настроить автоматический экспорт при каждом коммите через git hooks:

```bash
# .git/hooks/pre-commit
#!/bin/bash
python export_api_docs.py
git add openapi.json
```

## Публикация документации

### Вариант 1: GitHub Pages + Redoc

1. Создайте HTML файл с Redoc:
```html
<!DOCTYPE html>
<html>
  <head>
    <title>API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
      body { margin: 0; padding: 0; }
    </style>
  </head>
  <body>
    <redoc spec-url='openapi.json'></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"> </script>
  </body>
</html>
```

2. Разместите на GitHub Pages

### Вариант 2: Netlify / Vercel

Загрузите `openapi.json` и используйте Redoc для отображения.
