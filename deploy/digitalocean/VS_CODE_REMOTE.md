# Разработка на сервере через VS Code (Remote SSH)

Проект на дроплете: каталог **`/home/brainstorm/liveblog_project`** (корень репозитория: `venv/`, `liveblog_project/manage.py`, …).

## Быстрый старт (IP уже актуальный, например `161.35.19.91`)

1. Откройте **локальный** VS Code на Mac.
2. **`Cmd + Shift + P`** → введите **`Remote-SSH: Connect to Host…`** → выберите ваш хост (например `brainstorm-server`).
3. Дождитесь статуса слева внизу (**SSH: …**) — сессия на сервере активна.
4. **File → Open Folder…** → **`/home/brainstorm/liveblog_project`** → **OK** → при запросе доверия — **Yes**.
5. Если предложат **установить расширения на SSH** (Python, Pylance) — **Install**.
6. **`Cmd + Shift + P`** → **Python: Select Interpreter** → **`./venv/bin/python`**.
7. **Terminal → New Terminal** — оболочка на сервере; файлы редактируете в дереве слева.
8. После правок в **`.py`**: **`systemctl --user restart liveblog-gunicorn`** или **Tasks: Run Task** → **Restart Gunicorn (user service)**.

Готово: сохраняете файл (`Cmd+S`) — на диске сервера лежит актуальная версия; после перезапуска Gunicorn это видно на сайте.

## 1. Расширения на Mac

В VS Code установите:

- **Remote - SSH** (`ms-vscode-remote.remote-ssh`)
- **Python** (`ms-python.python`)
- **Pylance** (`ms-python.vscode-pylance`)

При открытии папки проекта VS Code предложит расширения из `.vscode/extensions.json`.

## 2. SSH config на Mac

Откройте `~/.ssh/config` и **убедитесь, что нет второго блока** с тем же IP и **`User root`** — VS Code может брать не тот блок, тогда будет **timeout** или **publickey**.

Готовый блок (можно скопировать из `deploy/digitalocean/ssh_config.example`):

```sshconfig
Host brainstorm-server
    HostName 161.35.19.91
    User brainstorm
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ConnectTimeout 60
    ServerAliveInterval 30
    TCPKeepAlive yes
```

Если ключ не `id_ed25519`, укажите свой путь (например `~/.ssh/id_rsa`).

Проверка в Terminal на Mac: `ssh brainstorm-server` (без пароля, если ключ в `authorized_keys` у `brainstorm`).

### VS Code: увеличить таймаут Remote SSH

**Settings → User → JSON** (или `Cmd+,` → иконка «Открыть settings.json») добавьте фрагмент из `deploy/digitalocean/vscode_user_settings_snippet.json`, например:

```json
"remote.SSH.connectTimeout": 120,
"remote.SSH.useLocalServer": true
```

## 2a. Если «Open Folder» / OK не открывает проект

- Ищите скрытое окно **«Do you trust the authors…»** (другой монитор / Cmd+`).
- Путь папки: **`/home/brainstorm/liveblog_project`** (без опечаток).
- **File → Open Folder…** и снова **OK** после **Developer: Reload Window**.

## 3. Подключение в VS Code

`Cmd+Shift+P` → **Remote-SSH: Connect to Host…** → **brainstorm-server**.

После входа: **File → Open Folder** →

`/home/brainstorm/liveblog_project`

В проводнике будет структура как в git: `liveblog_project/manage.py`, приложения, `venv/`, `.env` (локально не коммитится).

## 4. Интерпретатор Python

`Cmd+Shift+P` → **Python: Select Interpreter** →

`/home/brainstorm/liveblog_project/venv/bin/python`

В репозитории уже задано в `.vscode/settings.json` (`python.defaultInterpreterPath`).

## 5. Терминал

Откройте терминал в VS Code (**Terminal → New Terminal**): по умолчанию рабочая папка — `liveblog_project/` (где `manage.py`).

При необходимости:

```bash
source ../venv/bin/activate
```

## 6. Команды Django

Из каталога с `manage.py` (или через задачи VS Code, см. ниже):

```bash
../venv/bin/python manage.py check
../venv/bin/python manage.py migrate
../venv/bin/python manage.py collectstatic --noinput
```

## 7. Перезапуск приложения в проде (Gunicorn)

Публичный сайт идёт через **Nginx → Gunicorn**. Gunicorn у вас в **пользовательском** systemd, не системном.

После правок в коде **Python / шаблонах**, которые должен подхватить Gunicorn:

```bash
systemctl --user restart liveblog-gunicorn
systemctl --user status liveblog-gunicorn --no-pager
```

Либо в VS Code: `Cmd+Shift+P` → **Tasks: Run Task** → **Restart Gunicorn (user service)**.

Не используйте `sudo systemctl restart gunicorn` — такого unit на вашей настройке нет.

**Важно:** не запускайте `runserver 0.0.0.0:8000` на порту **8000**, пока работает Gunicorn — порт занят. Для временных экспериментов с отладкой лучше отдельный порт и осознанно менять `DJANGO_DEBUG` в `.env` (по умолчанию в проде `false`).

## 8. Задачи VS Code (`Cmd+Shift+B` / Run Task)

В `.vscode/tasks.json` настроено:

- Django: migrate  
- Django: collectstatic  
- Django: check  
- Restart Gunicorn (user service)  

## 9. Безопасность

- **`.env`** не коммитить (уже в `.gitignore`).
- Вход по **SSH-ключу**; по желанию отключить парольный вход и `PermitRootLogin no` в `sshd_config` (делается один раз с `sudo`).
- Редактирование только через VS Code + SSH (как вы и хотите), не через FTP.

## 10. Про «мгновенные» изменения

Gunicorn **сам** не перезагружается при сохранении файла — после изменения кода выполняйте **restart** пользовательского сервиса (см. §7). Шаблоны иногда можно увидеть после одного перезапуска воркера; при сомнениях — тот же restart.

Команда `runserver` в Django и так делает auto-reload в режиме разработки; отдельный `pip install watchdog` для этого **не обязателен**. Флага `manage.py runserver --reload` у Django нет.

---

## 11. Ошибка «Connecting with SSH timed out»

Это **не** про папку `liveblog_project`: соединение **не доходит** до нормального SSH (сеть или firewall).

1. На Mac: **`ssh -v brainstorm-server`** — если тут тоже долго и обрыв, проверьте:
   - дроплет **включён** в DigitalOcean;
   - **Cloud Firewall**: входящий **TCP 22** разрешён (или с вашего IP, или временно с `0.0.0.0/0`);
   - **VPN / другая Wi‑Fi сеть** — попробуйте отключить VPN или сменить сеть.
2. В `~/.ssh/config` добавьте **`ConnectTimeout 60`** и **`TCPKeepAlive yes`** (см. §2).
3. В VS Code увеличьте **`remote.SSH.connectTimeout`** (см. выше).
4. Лог: панель **Output** → в списке **Remote - SSH** — по шагам видно, где обрыв.

## 12. Ошибка «Permission denied (publickey)»

- Подключайтесь к хосту **`brainstorm-server`**, не к голому IP без нужного `User`.
- В config должен быть **`User brainstorm`**, не `root`, и строка **`IdentityFile`** на ключ, чья **`.pub`** лежит в `/home/brainstorm/.ssh/authorized_keys` на сервере.

## 13. Логи Remote SSH (диагностика)

**Cmd+Shift+P** → **Remote-SSH: Show Log** — сохраните вывод при обращении в поддержку или при отладке.
