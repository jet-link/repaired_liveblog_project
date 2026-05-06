# Переход с SQLite на PostgreSQL

## 1. Установка (уже выполнено)

```bash
brew install postgresql
brew services start postgresql
```

## 2. Создание базы данных

```bash
# Создать БД (используется текущий пользователь macOS)
createdb liveblog
```

## 3. Установка зависимостей

```bash
pip install psycopg2-binary python-dotenv
# или
pip install -r requirements.txt
```

## 4. Настройка .env

Скопируйте `.env.example` в `.env` и настройте:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```
DJANGO_DB_ENGINE=postgresql
DJANGO_DB_NAME=liveblog
DJANGO_DB_USER=ВАШ_USERNAME  # whoami в терминале
DJANGO_DB_PASSWORD=          # пусто для local peer auth
DJANGO_DB_HOST=localhost
DJANGO_DB_PORT=5432
```

## 5. Перенос данных (если есть данные в SQLite)

### Вариант A: Чистая миграция (новые данные)

```bash
cd liveblog_project
export DJANGO_DB_ENGINE=postgresql
python manage.py migrate
python manage.py createsuperuser  # создать админа
```

### Вариант B: Перенос существующих данных

```bash
cd liveblog_project

# 1. Экспорт из SQLite (с SQLite)
export DJANGO_DB_ENGINE=sqlite
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -o pre_migration_backup.json

# 2. Создать БД и мигрировать схему (PostgreSQL)
export DJANGO_DB_ENGINE=postgresql
python manage.py migrate

# 3. Загрузить данные
python manage.py loaddata pre_migration_backup.json

# 4. Сбросить пароли/сессии при необходимости
python manage.py clearsessions
```

## 6. Проверка

```bash
python manage.py runserver
```

Откройте http://127.0.0.1:8000 — проект должен работать на PostgreSQL.

## Откат на SQLite

Удалите или закомментируйте `DJANGO_DB_ENGINE=postgresql` в `.env`, либо:
```bash
unset DJANGO_DB_ENGINE
```

---

## Возможности PostgreSQL в проекте

При использовании PostgreSQL включаются:

### Полнотекстовый поиск (FTS)
- **title** и **text** — полнотекстовый поиск с ранжированием (SearchVector, SearchRank)
- Поддержка фраз, AND/OR (`search_type='websearch'`)
- Конфиг `simple` — поддержка разных языков (в т.ч. кириллица)
- GIN-индекс на `title` и `text` для ускорения поиска

### Фильтр «Популярное»
- Формула времени: `likes / (часы_с_публикации + 2)^1.5`
- Сортировка по популярности в БД (без загрузки в Python)
- Учитывает «свежесть» публикаций — недавние с лайками выше в списке

### Фильтры «Понравилось» и «Закладки»
- Остаются как раньше: фильтрация по текущему пользователю
- Сортировка по дате добавления (Subquery)
