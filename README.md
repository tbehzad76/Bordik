# بوردیک (Bordik) — مدیریت پروژه و وظایف تیمی

اپلیکیشن شبیه ترللو برای شرکت: هر کاربر با شماره همراه ثبت‌نام می‌کند، پروژه می‌سازد، همکاران را با شماره همراه عضو می‌کند و کارت‌ها را بین ستون‌ها جابه‌جا می‌کند. هر کارت می‌تواند چند مسئول داشته باشد.

پشته فناوری: FastAPI، Jinja2، SQLAlchemy، PostgreSQL (یا SQLite برای توسعه)، Alembic، JWT و Argon2.

## امکانات

- ثبت‌نام و ورود با شماره همراه و رمز عبور
- پروژه (برد) با ستون‌های پیش‌فرض «برای انجام، در حال انجام، انجام‌شده»
- ساخت، حذف و تغییر نام/نوع ستون‌ها توسط مالک پروژه
- کارت با عنوان، توضیحات، سررسید (تاریخ مشخص یا تعداد روز) و چند مسئول
- تاریخ‌ها و دیت‌پیکر جلالی (شمسی) در رابط وب
- نمایش «چند روز مانده / امروز / چند روز تأخیر» روی کارت‌ها
- حذف کارت فقط توسط سازندهٔ همان کارت (مالک پروژه فقط برای کارت‌های بدون سازنده)
- جابه‌جایی کارت بین ستون‌ها با درگ‌اند‌دراپ و ترتیب دلخواه
- عضویت با شماره همراه؛ اگر کاربر ثبت‌نام نکرده باشد، دعوت در انتظار می‌ماند و پس از ثبت‌نام خودکار فعال می‌شود (بدون نیاز به پیامک)
- نقش مالک و عضو با دسترسی‌های جداگانه
- رابط وب فارسی و راست‌به‌چپ + REST API مستند در `/docs`
- فونت وزیرمتن به‌صورت لوکال همراه پروژه است (بدون نیاز به اینترنت)

## راه‌اندازی

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

کلید JWT را روی یک مقدار تصادفی بگذارید:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

مقدار را در `.env` کنار `JWT_SECRET_KEY` قرار دهید.

## اجرا

```powershell
uvicorn task_manager.main:app --reload --host 0.0.0.0 --port 8000
```

- رابط وب: `http://127.0.0.1:8000/`
- مستندات API: `http://127.0.0.1:8000/docs`

## دیتابیس

برای توسعه، SQLite کافی است:

```env
DATABASE_URL=sqlite:///./tasks.db
AUTO_CREATE_TABLES=true
```

برای اجرا در شرکت PostgreSQL را توصیه می‌کنیم:

```env
DATABASE_URL=postgresql+psycopg://tasks_user:strong-password@127.0.0.1:5432/tasks
AUTO_CREATE_TABLES=false
COOKIE_SECURE=true
```

سپس مهاجرت‌ها را اجرا کنید:

```powershell
alembic upgrade head
```

- در حالت توسعه، جدول‌ها خودکار ساخته می‌شوند (`AUTO_CREATE_TABLES=true`).
- در محیط واقعی، `AUTO_CREATE_TABLES=false` بگذارید و فقط با Alembic مهاجرت کنید.
- برای HTTPS (پشت Nginx یا Caddy) حتماً `COOKIE_SECURE=true` باشد.

## تست

```powershell
pytest
```

تست‌ها روی SQLite موقت اجرا می‌شوند و به PostgreSQL نیاز ندارند.

## نکته شماره همراه

شماره‌ها یکدست‌سازی می‌شوند؛ مثلاً `09121234567` به `+989121234567` تبدیل می‌شود. ارقام فارسی/عربی، فاصله، خط تیره و پرانتز پذیرفته می‌شود. کد کشور پیش‌فرض در `task_manager/phones.py` قابل تغییر است.

## API (خلاصه)

| متد | مسیر | توضیح |
| --- | --- | --- |
| POST | `/api/auth/register` | ثبت‌نام |
| POST | `/api/auth/login` | ورود و دریافت JWT |
| GET | `/api/auth/me` | کاربر جاری |
| GET | `/api/projects` | پروژه‌های من |
| POST | `/api/projects` | ساخت پروژه |
| GET | `/api/projects/{id}` | برد کامل |
| PATCH | `/api/projects/{id}` | ویرایش پروژه (مالک) |
| DELETE | `/api/projects/{id}` | حذف پروژه (مالک) |
| GET | `/api/projects/{id}/members` | اعضا |
| POST | `/api/projects/{id}/members` | افزودن عضو/دعوت با شماره |
| DELETE | `/api/projects/{id}/members/{user_id}` | حذف عضو (مالک) |
| POST | `/api/projects/{id}/columns` | ساخت ستون (مالک) |
| PATCH | `/api/projects/{id}/columns/{column_id}` | ویرایش ستون (مالک) |
| DELETE | `/api/projects/{id}/columns/{column_id}` | حذف ستون خالی (مالک) |
| POST | `/api/projects/{id}/cards` | ساخت کارت |
| GET | `/api/projects/{id}/cards/{card_id}` | یک کارت |
| PATCH | `/api/projects/{id}/cards/{card_id}` | ویرایش کارت |
| PUT | `/api/projects/{id}/cards/{card_id}/assignees` | تعیین مسئولان |
| POST | `/api/projects/{id}/cards/{card_id}/move` | جابه‌جایی کارت |
| DELETE | `/api/projects/{id}/cards/{card_id}` | حذف کارت (فقط سازنده) |

مسیرهای `/api` فقط توکن Bearer می‌پذیرند:
```text
Authorization: Bearer <access_token>
```

نمونه ثبت‌نام:

```json
{
  "full_name": "سارا محمدی",
  "phone": "09121234567",
  "password": "strong-password"
}
```

## اجرا با Docker

فایل‌های آماده در ریشه پروژه: `Dockerfile`، `docker-compose.yml`، `.env.docker.example`.
اپ **app** هنگام بالا آمدن خودش `alembic upgrade head` را اجرا می‌کند و دیتابیس PostgreSQL در یک volume ماندگار ذخیره می‌شود.

### پیش‌نیاز مشترک

1. Docker و افزونهٔ Compose نصب باشد.
2. پروژه را کلون کن:
   ```bash
   git clone https://github.com/tbehzad76/Bordik.git
   cd Bordik
   ```
3. فایل محیطی بساز:
   ```bash
   cp .env.docker.example .env
   chmod 600 .env
   ```
4. دو مقدار امن بساز و در `.env` بگذار:
   ```env
   JWT_SECRET_KEY=<رشته تصادفی حداقل ۳۲ کاراکتری>
   POSTGRES_PASSWORD=<رمز قوی دیتابیس>
   APP_PORT=8000
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   COOKIE_SECURE=false
   WEB_CONCURRENCY=2
   ```
   ساخت مقدار تصادفی:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   openssl rand -base64 24
   ```

> `COOKIE_SECURE` را فقط وقتی `true` کن که دامنه‌ات HTTPS دارد.

---

### لینوکس (Ubuntu / Debian)

نصب Docker:
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```
یک‌بار از سرور خارج و دوباره وارد شو، بعد بررسی کن:
```bash
docker --version
docker compose version
```

بیلد و اجرا:
```bash
docker compose up --build -d
docker compose ps
docker compose logs -f app
```

بررسی سلامت:
```bash
curl http://127.0.0.1:8000/health
```
باید `{"status":"ok"}` برگردد. در مرورگر: `http://IP-سرور:8000`.

فایروال:
```bash
sudo ufw allow 22,80,443/tcp
# اگر فعلاً بدون دامنه و روی پورت ۸۰۰۰ می‌خواهی:
sudo ufw allow 8000/tcp
```

---

### ویندوز (Docker Desktop)

> Docker Desktop روی Windows 10/11 (با WSL2) پشتیبانی می‌شود و روی Windows Server پشتیبانی رسمی ندارد؛ برای Windows Server یک VM لینوکس یا WSL2 توصیه می‌شود.
> ایمیج Linux است، پس Docker Desktop باید در حالت **Linux containers** باشد.

پیش‌نیازها:
```powershell
wsl --install
wsl --set-default-version 2
winget install --id Git.Git -e
```
Docker Desktop را نصب کن، بازش کن و گزینهٔ «Start Docker Desktop when you sign in» را روشن بگذار. سپس:
```powershell
docker --version
docker compose version
docker info
```

گرفتن پروژه:
```powershell
New-Item -ItemType Directory -Force C:\apps | Out-Null
Set-Location C:\apps
git clone https://github.com/tbehzad76/Bordik.git
Set-Location C:\apps\Bordik
Copy-Item .env.docker.example .env
notepad .env
```
ساخت مقدار تصادفی:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
# بدون پایتون:
[Convert]::ToBase64String((New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes(36))
```

بیلد و اجرا:
```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f app
```

بررسی سلامت:
```powershell
Invoke-RestMethod http://localhost:8000/health
```
دسترسی از شبکهٔ شرکت (PowerShell ادمین):
```powershell
New-NetFirewallRule -DisplayName "Bordik 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
ipconfig
```
سپس از سیستم‌های دیگر: `http://<IP-سرور>:8000`.

---

### HTTPS با دامنه (Caddy)

یک فایل `Caddyfile` بساز:
```text
bordik.example.com {
    reverse_proxy app:8000
}
```
و یک فایل `docker-compose.https.yml`:
```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - app

volumes:
  caddy_data:
  caddy_config:
```
`COOKIE_SECURE=true` را در `.env` بگذار و اجرا کن:
```bash
docker compose -f docker-compose.yml -f docker-compose.https.yml up --build -d
```
دامنه باید به IP سرور اشاره کند و پورت‌های ۸۰ و ۴۴۳ از اینترنت باز باشند.

---

### به‌روزرسانی

```bash
git pull
docker compose up --build -d
```
مهاجرت‌های Alembic هنگام استارت خودکار اجرا می‌شوند.

### بکاپ و بازیابی

Linux:
```bash
docker compose exec db pg_dump -U tasks -d tasks -f /tmp/backup.sql
docker compose cp db:/tmp/backup.sql ./backup.sql
docker compose cp ./backup.sql db:/tmp/backup.sql
docker compose exec db psql -U tasks -d tasks -f /tmp/backup.sql
```
Windows:
```powershell
docker compose exec db pg_dump -U tasks -d tasks -f /tmp/backup.sql
docker compose cp db:/tmp/backup.sql .\backup.sql
docker compose cp .\backup.sql db:/tmp/backup.sql
docker compose exec db psql -U tasks -d tasks -f /tmp/backup.sql
```

### عیب‌یابی Docker

```bash
docker compose logs -f app db
docker compose ps
docker compose restart app
docker compose exec app alembic current
```
- app پشت‌سرهم ری‌استارت می‌شود؟ معمولاً `JWT_SECRET_KEY` ست نشده یا کمتر از ۳۲ کاراکتر است.
- خطای ۵۰۲ از reverse proxy یعنی app هنوز سالم نشده؛ `docker compose logs -f app` را ببین.
- روی ویندوز اگر پورت اشغال بود: `netstat -ano | findstr :8000`.
- داده‌ها با `docker compose down` می‌مانند و فقط `docker compose down -v` آن‌ها را پاک می‌کند.

#### اگر build در مرحلهٔ pip شکست خورد

لاگ کامل را ببین:
```bash
docker compose build --no-cache --progress=plain app
```
دلیل رایج، دسترسی‌نداشتن کانتینر build به PyPI است (اغلب به‌خاطر پروکسی). در **Docker Desktop → Settings → Resources → Proxies**:
- یا گزینهٔ «No proxy» را بزن،
- یا آدرس پروکسی میزبان را با `host.docker.internal` بده، نه `127.0.0.1`؛ مثلاً `http://host.docker.internal:10808`.

سپس Apply & Restart و دوباره `docker compose up --build -d`.

## عیب‌یابی ورود

حساب‌ها در دیتابیس ذخیره می‌شوند. اگر بین ثبت‌نام و ورود فایل دیتابیس عوض یا پاک شود، حساب از بین می‌رود و پیام «رمز عبور نادرست» دیده می‌شود.

- مسیرهای نسبی SQLite حالا نسبت به ریشه پروژه حل می‌شوند، پس مهم نیست از چه پوشه‌ای سرور را اجرا کنی.
- در حالت توسعه، برای دیدن کاربران ثبت‌شده:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('tasks.db'); print(list(c.execute('select id, phone, full_name from users')))"
```

- اگر `tasks.db` قدیمی (قبل از تغییر به شماره همراه) داری، فایل را پاک کن و سرور را دوباره اجرا کن.
- در Docker، داده‌ها در volume `pgdata` می‌مانند؛ `docker compose down -v` همه را پاک می‌کند.

## سررسید کارت

هر کارت می‌تواند یکی از این دو را داشته باشد:

- `due_date`: تاریخ میلادی مثل `2030-01-02`
- `due_in_days`: تعداد روز از امروز

در پاسخ API فیلد محاسبه‌شدهٔ `days_remaining` و `due_date_jalali` هم برمی‌گردد. در رابط وب تاریخ‌ها جلالی هستند و دیت‌پیکر جلالی داخل خود پروژه (بدون وابستگی اینترنتی) پیاده‌سازی شده است. با گزینهٔ «حذف سررسید» می‌توانی تاریخ را پاک کنی.

## امنیت

- رمز عبور با Argon2 هش می‌شود.
- API فقط Bearer token می‌پذیرد؛ کوکی نشست مخصوص رابط وب است.
- فرم‌ها با CSRF token محافظت می‌شوند؛ درخواست‌های درگ‌اند‌دراپ با هدر `X-CSRF-Token`.
- هدرهای امنیتی CSP، `X-Frame-Options`، `X-Content-Type-Options` و `Referrer-Policy` فعال هستند.
- هر کاربر فقط به پروژه‌های خودش دسترسی دارد؛ غیرعضو پاسخ ۴۰۴ می‌گیرد.
- فقط مالک پروژه می‌تواند اعضا و ستون‌ها را مدیریت کند.
- حذف کارت فقط توسط سازندهٔ همان کارت انجام می‌شود.
- کلید JWT از `.env` خوانده می‌شود و در Git نادیده گرفته می‌شود.
