# todo-tracker

Нативный `menu bar` todo-tracker для macOS на Python. Приложение живёт в верхнем меню, хранит заметки в локальной `SQLite` базе и открывает кастомный popup со списком задач, редактированием и дедлайнами.

## Что уже умеет

- открываться из menu bar как отдельное macOS-приложение без иконки в Dock
- показывать задачи в popup-окне фиксированной ширины и с ограничением по высоте
- прокручивать список, если задач много
- помечать задачу как `done` по левому переключателю
- переносить выполненные задачи вниз списка и зачеркивать их
- раскрывать текст заметки по стрелке рядом с заголовком
- показывать `edit` и `delete` только при наведении на строку
- добавлять и редактировать заметки во встроенной нижней форме
- выбирать приоритет `low / medium / high`
- добавлять опциональный дедлайн через нативный `date picker`

## Стек

- Python 3.11+
- `uv` для зависимостей и запуска
- `rumps` + `PyObjC/AppKit` для menu bar UI
- `SQLAlchemy` для модели данных и хранения
- `SQLite` как локальная база
- `Typer` для CLI-команд
- `py2app` для сборки `.app`

## Установка зависимостей

```bash
uv sync --dev
```

## Запуск из исходников

CLI:

```bash
uv run todo-tracker list
```

Menu bar app:

```bash
PYTHONPATH=src .venv/bin/python -m todo_tracker.menubar
```

По умолчанию база лежит в:

```bash
~/.todo_tracker.db
```

## CLI-команды

Добавить задачу:

```bash
uv run todo-tracker add --title "Купить молоко" --content "2 бутылки" --priority low
```

Добавить задачу с дедлайном:

```bash
uv run todo-tracker add --title "Отправить отчёт" --content "PDF" --priority high --due-date "2026-06-01T18:30:00"
```

Показать активные задачи:

```bash
uv run todo-tracker list
```

Обновить задачу по номеру из текущего списка:

```bash
uv run todo-tracker update 1 --title "Купить хлеб" --content "Ржаной" --priority medium
```

Пометить задачу как выполненную:

```bash
uv run todo-tracker done 1
```

Удалить все задачи со статусом `done`:

```bash
uv run todo-tracker delete
```

## Правила модели и сортировки

- статусы: `in_progress`, `done`, `archived`
- приоритеты: `high`, `medium`, `low`
- в GUI задачи сортируются так:
  - сначала `in_progress`
  - потом `done`
  - внутри группы: `high -> medium -> low`
  - затем по дедлайну
  - затем по времени создания
- CLI-команды `update <num>` и `done <num>` работают по номеру из текущего вывода `list`, а не по `id` записи в базе

## Сборка `.app`

Сборка делается через `py2app`, который уже подключён как dev-зависимость.

Собрать приложение из корня репозитория:

```bash
cd app_bundle
../.venv/bin/python setup.py py2app
```

После сборки bundle появится здесь:

```bash
app_bundle/dist/TodoTracker.app
```

Полная команда сборки в одну строку из корня репозитория:

```bash
cd app_bundle && ../.venv/bin/python setup.py py2app
```

Если нужен bundle в привычном корневом `dist/`, скопируйте его отдельной командой из корня репозитория:

```bash
rm -rf dist/TodoTracker.app && cp -R app_bundle/dist/TodoTracker.app dist/TodoTracker.app
```

Если вы уже находитесь внутри `app_bundle/`, используйте:

```bash
rm -rf ../dist/TodoTracker.app && cp -R dist/TodoTracker.app ../dist/TodoTracker.app
```

Готовый app для запуска и добавления в автозапуск:

```bash
dist/TodoTracker.app
```

## Автозапуск через настройки macOS

1. Откройте `System Settings`
2. Перейдите в `General`
3. Откройте `Login Items`
4. Нажмите `+`
5. Выберите [TodoTracker.app](/Users/artem/Programming/todo_tracker/dist/TodoTracker.app)

Если приложение уже было добавлено раньше, а вы пересобрали bundle, лучше удалить старую запись и добавить её заново.

## Тесты

Запуск всех тестов:

```bash
uv run pytest -q
```

## Файлы сборки

- [src/todo_tracker/menubar.py](/Users/artem/Programming/todo_tracker/src/todo_tracker/menubar.py) — entrypoint menu bar приложения
- [src/todo_tracker/popup.py](/Users/artem/Programming/todo_tracker/src/todo_tracker/popup.py) — popup UI и контроллер
- [src/todo_tracker/geometry.py](/Users/artem/Programming/todo_tracker/src/todo_tracker/geometry.py) — геометрия позиционирования popup
- [app_bundle/setup.py](/Users/artem/Programming/todo_tracker/app_bundle/setup.py) — сборка `.app` через `py2app`
