# Video Downloader

Автономный инструмент для скачивания видео с конференций и платформ, требующих аутентификации через браузерные куки.

## Возможности

- Скачивание видео с сайтов конференций (JPoint, Heisenbug, HolyJS, Mobius)
- Использование браузерных куки для аутентификации
- Поддержка Chrome, Brave, Edge, Chromium
- Автоматическое определение профилей браузера
- Обход DRM через официальные ссылки скачивания
- Поддержка HLS/DASH потоков
- Возобновление прерванных загрузок

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd video_downloader
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Установите браузеры для Playwright (опционально):
```bash
playwright install chromium
```

## Конфигурация

Отредактируйте `config.toml`:

```toml
# Браузер для чтения куки
browser = "chrome"

# Профиль браузера (например, "Игорь", "Default", "Profile 1")
browser_profile = "Игорь"

# Корневая директория для загрузок
output_root = "downloads"

# Файл со ссылками (один URL на строку)
links_file = "links.txt"

# Опционально: путь к cookies.txt (формат Netscape)
# cookies_file = "cookies.txt"
```

## Использование

### Подготовка ссылок

Добавьте URL в файл `links.txt` (по одному на строку):
```
https://jpoint.ru/talks/example-talk-id/
https://heisenbug.ru/archive/2025%20Spring/talks/example-id/
```

### Запуск

```bash
# Основной способ
python main.py

# С аргументами командной строки
python main.py https://example.com/video/ --browser chrome --browser-profile "Игорь"

# Через модуль Python
python -m src.cli https://example.com/video/
```

### CLI параметры

```bash
python main.py [URLs...] --browser chrome --browser-profile "Игорь" --output-root downloads/
```

## Поддерживаемые платформы

- **JPoint** (jpoint.ru)
- **Heisenbug** (heisenbug.ru) 
- **HolyJS** (holyjs.ru)
- **Mobius** (mobiusconf.com)
- Другие сайты с HLS/DASH потоками

## Требования

- Python 3.8+
- Браузер с установленными куки (Chrome/Brave/Edge/Chromium)
- FFmpeg (для обработки видео)

## Структура проекта

```
video_downloader/
├── main.py             # Главная точка входа
├── config.toml         # Конфигурация
├── links.txt          # Список URL для скачивания
├── requirements.txt   # Зависимости
├── src/               # Исходный код
│   ├── config.py      # Управление конфигурацией
│   ├── browser.py     # Браузерные профили
│   ├── downloader.py  # Основная логика скачивания
│   ├── file_manager.py # Управление файлами
│   ├── playwright_capture.py # Браузерное скачивание
│   ├── utils.py       # Вспомогательные функции
│   └── cli.py         # CLI интерфейс
├── tests/             # Тесты
│   ├── test_config.py
│   ├── test_file_manager.py
│   └── test_utils.py
└── README.md         # Документация
```

## Алгоритм работы

1. **Пробное скачивание**: Попытка через yt-dlp с браузерными куки
2. **Захват манифеста**: Если не поддерживается, используется Playwright для захвата HLS/DASH манифеста
3. **Определение DRM**: Эвристическое определение защиты контента
4. **Официальное скачивание**: При обнаружении DRM - переход на официальный поток скачивания через браузер
5. **Обработка**: FFmpeg для финальной обработки и оптимизации

## Устранение неполадок

### Проблемы с куки
- Убедитесь, что вы авторизованы в браузере на целевом сайте
- Проверьте правильность профиля браузера в `config.toml`
- Попробуйте экспортировать куки через расширение "Get cookies.txt"

### Проблемы с DRM
- Инструмент автоматически переключается на официальное скачивание
- Убедитесь, что у вас есть доступ к скачиванию на сайте
- Некоторые видео могут быть недоступны для скачивания

### Проблемы с Playwright
- Установите браузеры: `playwright install chromium`
- Проверьте права доступа к профилю браузера
- Попробуйте другой браузер в конфигурации

## Лицензия

MIT License
