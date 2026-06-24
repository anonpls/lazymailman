# Запуск Lazy Mailman как Systemd Service на Linux сервере

## Инструкция по установке

### 1. Подготовьте сервер

Скопируйте проект на сервер:
```bash
scp -r ~/Dev/lazymailman user@your-server:/opt/
```

### 2. Создайте пользователя для сервиса (опционально, но рекомендуется)

```bash
sudo useradd -r -s /bin/false mailman
```

### 3. Установите права доступа

```bash
sudo chown -R mailman:mailman /opt/lazymailman
sudo chmod 750 /opt/lazymailman
```

### 4. Создайте директорию для логов

```bash
sudo mkdir -p /var/log/lazymailman
sudo chown mailman:mailman /var/log/lazymailman
sudo chmod 755 /var/log/lazymailman
```

### 5. Скопируйте .service файл в systemd

```bash
sudo cp /opt/lazymailman/lazymailman.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 6. Убедитесь, что .env файл находится на месте

```bash
sudo nano /opt/lazymailman/.env
```

Содержимое примерно такого вида:
```env
EMAIL_SENDER=sender@example.com
GMAIL_APP_PASSWORD=your-gmail-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SUBJECT=Тест письма
EMAIL_TEXT=Здравствуйте!
```

### 7. Проверьте, что Python установлен

```bash
python3 --version
```

## Команды управления сервисом

### Запуск сервиса
```bash
sudo systemctl start lazymailman
```

### Остановка сервиса
```bash
sudo systemctl stop lazymailman
```

### Перезагрузка сервиса
```bash
sudo systemctl restart lazymailman
```

### Автозапуск при перезагрузке сервера
```bash
sudo systemctl enable lazymailman
```

### Отключение автозапуска
```bash
sudo systemctl disable lazymailman
```

### Проверка статуса
```bash
sudo systemctl status lazymailman
```

### Просмотр логов в реальном времени
```bash
sudo journalctl -u lazymailman -f
```

### Просмотр последних 100 строк логов
```bash
sudo journalctl -u lazymailman -n 100
```

### Просмотр логов за последний час
```bash
sudo journalctl -u lazymailman --since "1 hour ago"
```

## Опции запуска с флагами

Если вам нужно запустить с флагами (например `--test` или `--rewriter`), отредактируйте `.service` файл:

```bash
sudo nano /etc/systemd/system/lazymailman.service
```

И измените строку `ExecStart`:

**Для тестового режима через Telegram:**
```ini
ExecStart=/usr/bin/python3 /opt/lazymailman/main.py --test
```

**С переформулировкой текста:**
```ini
ExecStart=/usr/bin/python3 /opt/lazymailman/main.py --rewriter
```

**С кастомной задержкой между отправками (в секундах):**
```ini
ExecStart=/usr/bin/python3 /opt/lazymailman/main.py --send-delay 2.5
```

Затем перезагрузите конфиг и перезапустите сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl restart lazymailman
```

## Проблемы и решения

### Сервис не запускается
Проверьте логи:
```bash
sudo systemctl status lazymailman
sudo journalctl -u lazymailman -n 50
```

### Ошибка "Permission denied"
Убедитесь в правах доступа:
```bash
sudo chown -R mailman:mailman /opt/lazymailman
sudo chmod 750 /opt/lazymailman
```

### Python не найден
Проверьте путь к Python:
```bash
which python3
```

И используйте полный путь в `.service` файле (обычно `/usr/bin/python3`).

### Ошибки с .env файлом
Убедитесь, что файл читаем:
```bash
sudo chmod 640 /opt/lazymailman/.env
```

## Примеры использования

**Пример 1: Простой запуск для отправки писем**
```bash
sudo systemctl start lazymailman
sudo systemctl enable lazymailman  # автозапуск при перезагрузке
sudo journalctl -u lazymailman -f  # смотреть логи
```

**Пример 2: Тестирование через Telegram перед реальной рассылкой**
Отредактируйте `.service` с флагом `--test`, запустите, проверьте логи.

**Пример 3: Мониторинг сервиса**
```bash
while true; do sudo systemctl status lazymailman; sleep 5; done
```
