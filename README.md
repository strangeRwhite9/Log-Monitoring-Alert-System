# Flask Web Security Project With Local Email Notifier

This version keeps your Gmail password off the deployed web app.

- The Flask web app handles login attempts.
- Failed logins are logged to `login.log`.
- Failed logins are also stored in a SQLite alert queue.
- A separate local Python program runs on your own machine and sends Gmail alerts.
- The hosted app and the local notifier talk through a token-protected API.

## Why this design is safer

Your Gmail app password stays only on your own computer in `.env.notifier`.

That means:

- Render does not need your Gmail password.
- Railway does not need your Gmail password.
- Your public Flask app only stores alert data like email, IP address, and time.

## Folder structure

```text
New project/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── routes.py
│   ├── services/
│   │   ├── alert_store.py
│   │   ├── auth_service.py
│   │   ├── email_service.py
│   │   ├── logging_service.py
│   │   └── security_service.py
│   ├── static/
│   │   └── styles.css
│   └── templates/
│       ├── base.html
│       ├── login.html
│       └── success.html
├── .env.example
├── .env.notifier.example
├── .gitignore
├── Procfile
├── README.md
├── local_notifier.py
├── requirements.txt
└── wsgi.py
```

## What the project does

1. A user enters email and password in the login form.
2. The app captures the client IP address.
3. If the login succeeds, the app shows a success page.
4. If the login fails:
   - the app writes `email`, `IP address`, and `timestamp` to `login.log`
   - the app stores an alert in `alerts.db`
   - after more than 5 failures from the same IP, the alert is marked as possible brute force
   - cooldown logic prevents too many duplicate alerts from the same IP
   - repeated failures add a short delay
5. Your local notifier program fetches pending alerts and sends Gmail emails from your own machine.

## Hardcoded test user

- Email: `student@example.com`
- Password: `SecurePass123!`

## Part 1: Run the Flask web app

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the server config

Copy `.env.example` to `.env`.

Example:

```env
SECRET_KEY=replace-this-with-a-random-secret
SESSION_COOKIE_SECURE=false
VALID_TEST_EMAIL=student@example.com
VALID_TEST_PASSWORD=SecurePass123!
ALERT_DB_FILE=alerts.db
NOTIFIER_API_TOKEN=change-this-shared-token
PENDING_ALERT_FETCH_LIMIT=20
ATTEMPT_WINDOW_SECONDS=900
BRUTE_FORCE_THRESHOLD=5
ALERT_COOLDOWN_SECONDS=300
DELAY_AFTER_FAILURES=3
LOCKOUT_DELAY_SECONDS=2
```

Important:

- `NOTIFIER_API_TOKEN` must be a long random secret string.
- The same token must also be used in `.env.notifier`.

### 4. Start the Flask app

```bash
flask --app wsgi run --debug
```

Open:

```text
http://127.0.0.1:5000
```

## Part 2: Run the local Gmail notifier

This program sends email from your own machine, not from Render.

### 1. Create the notifier config

Copy `.env.notifier.example` to `.env.notifier`.

Example:

```env
SOURCE_APP_URL=http://127.0.0.1:5000
NOTIFIER_API_TOKEN=change-this-shared-token
ADMIN_EMAIL=strangerwhite9@gmail.com
ADMIN_APP_PASSWORD=your-16-character-gmail-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
POLL_INTERVAL_SECONDS=60
PENDING_ALERT_FETCH_LIMIT=20
NOTIFIER_LOG_FILE=notifier.log
```

### 2. Set up Gmail App Password

1. Sign in to `strangerwhite9@gmail.com`.
2. Turn on Google 2-Step Verification.
3. Open Google Account `Security`.
4. Open `App passwords`.
5. Create an app password for Mail.
6. Copy the 16-character password.
7. Put it into `ADMIN_APP_PASSWORD` in `.env.notifier`.

Important:

- Do not use your normal Gmail password.
- Do not upload `.env.notifier` to GitHub.

### 3. Run the notifier once

```bash
python3 local_notifier.py
```

### 4. Run the notifier continuously

```bash
python3 local_notifier.py --poll
```

When it runs:

- it fetches pending alerts from the Flask app
- sends Gmail emails to `strangerwhite9@gmail.com` and the entered user email
- marks the alert as sent so it does not send twice
- writes local worker activity to `notifier.log`

## Email content

The email includes:

- warning message
- submitted user email
- IP address
- timestamp
- `Possible brute force attack` when the threshold is exceeded

## Deploy on Render

Deploy only the Flask web app to Render.

Do not deploy `local_notifier.py`.

### Render settings

- Runtime: `Python 3`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn wsgi:app`

### Render environment variables

Set these in Render:

- `SECRET_KEY`
- `SESSION_COOKIE_SECURE=true`
- `VALID_TEST_EMAIL`
- `VALID_TEST_PASSWORD`
- `ALERT_DB_FILE=/var/data/alerts.db` if you attach a persistent disk
- `NOTIFIER_API_TOKEN`
- `PENDING_ALERT_FETCH_LIMIT`
- `ATTEMPT_WINDOW_SECONDS`
- `BRUTE_FORCE_THRESHOLD`
- `ALERT_COOLDOWN_SECONDS`
- `DELAY_AFTER_FAILURES`
- `LOCKOUT_DELAY_SECONDS`

### Local notifier with Render

After deployment, set this in your local `.env.notifier`:

```env
SOURCE_APP_URL=https://your-render-service.onrender.com
```

Keep running this on your own system:

```bash
python3 local_notifier.py --poll
```

## Production note

`alerts.db` and `login.log` are app-level files.

If you deploy to Render without a persistent disk:

- queued alerts can be lost after restart
- logs can be lost after restart

For better persistence on Render, attach a disk and set:

```env
ALERT_DB_FILE=/var/data/alerts.db
```

