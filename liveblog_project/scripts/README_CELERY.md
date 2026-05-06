# Celery: автозапуск (macOS launchd)

Worker и Beat объединены в один процесс `celery worker --beat` — trending и rollup обновляются автоматически.

## Быстрый запуск вручную

```bash
cd liveblog_project
./scripts/celery_dev.sh
```

Или через venv:

```bash
cd liveblog_project
../venv/bin/celery -A liveblog_project worker --beat -l info
```

---

## Автозапуск через launchd (фон, автозагрузка при входе в систему)

### Установка

1. **Redis должен быть запущен**  
   ```bash
   brew services start redis
   ```

2. **Установить сервис (одной командой):**
   ```bash
   cd liveblog_project
   ./scripts/install_celery_service.sh
   ```

   Или вручную:
   ```bash
   mkdir -p ~/Library/LaunchAgents
   cp liveblog_project/scripts/com.liveblog.celery.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.liveblog.celery.plist
   ```

3. **Проверить пути в plist** (если проект в другой директории):
   - Открыть `~/Library/LaunchAgents/com.liveblog.celery.plist`
   - Заменить `/Users/glaze_4life/pyPROJECTS/live-chat-blog` на свой путь к проекту

4. **Включить сервис:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.liveblog.celery.plist
   ```

5. **Проверить статус:**
   ```bash
   launchctl list | grep liveblog
   ```

   Должно быть `com.liveblog.celery` со статусом 0.

6. **Логи:**
   ```bash
   tail -f /tmp/celery-liveblog.log
   tail -f /tmp/celery-liveblog.err
   ```

### Остановка / удаление

```bash
launchctl unload ~/Library/LaunchAgents/com.liveblog.celery.plist
# При желании удалить plist:
# rm ~/Library/LaunchAgents/com.liveblog.celery.plist
```

### Перезапуск после изменений

```bash
launchctl unload ~/Library/LaunchAgents/com.liveblog.celery.plist
launchctl load ~/Library/LaunchAgents/com.liveblog.celery.plist
```

---

## Альтернатива: запуск в фоне без launchd

```bash
cd liveblog_project
nohup ./scripts/celery_dev.sh > /tmp/celery.log 2>&1 &
```

Остановка: `pkill -f "celery.*liveblog_project"`
