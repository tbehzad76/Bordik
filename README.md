# بوردیک (Bordik) — مدیریت پروژه و وظایف تیمی

اپلیکیشن شبیه ترللو برای شرکت: هر کاربر با شماره همراه ثبت‌نام می‌کند، پروژه می‌سازد، همکاران را با شماره همراه عضو می‌کند و کارت‌ها را بین ستون‌ها جابه‌جا می‌کند. هر کارت می‌تواند چند مسئول داشته باشد.

پشته فناوری: FastAPI، Jinja2، SQLAlchemy، PostgreSQL (یا SQLite برای توسعه)، Alembic، JWT و Argon2.

## امکانات

- ثبت‌نام و ورود با شماره همراه و رمز عبور
- پروژه (برد) با ستون‌های پیش‌فرض «برای انجام، در حال انجام، انجام‌شده»
- ساخت، حذف و تغییر نام/نوع ستون‌ها توسط مالک پروژه
- کارت با عنوان، توضیحات، سررسید (تاریخ مشخص یا تعداد روز) و چند مسئول
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

ابتدا فایل `.env` را از نمونه بساز و مقادیر `JWT_SECRET_KEY` و `POSTGRES_PASSWORD` را عوض کن:

```powershell
Copy-Item .env.docker.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

سپس:

```powershell
docker compose up --build -d
docker compose logs -f app
```

- برنامه: `http://localhost:8000`
- PostgreSQL در volume به نام `pgdata` ذخیره می‌شود؛ `docker compose down` داده‌ها را نگه می‌دارد و فقط `docker compose down -v` آن‌ها را پاک می‌کند.
- مهاجرت‌های Alembic هنگام بالا آمدن کانتینر خودکار اجرا می‌شوند.
- اگر پشت HTTPS اجرا می‌کنی، `COOKIE_SECURE=true` بگذار.

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

در پاسخ API فیلد محاسبه‌شدهٔ `days_remaining` هم برمی‌گردد (عدد منفی یعنی تأخیر). در صفحهٔ کارت هر دو گزینه موجود است و با «حذف سررسید» می‌توانی آن را پاک کنی.

## امنیت

- رمز عبور با Argon2 هش می‌شود.
- API فقط Bearer token می‌پذیرد؛ کوکی نشست مخصوص رابط وب است.
- فرم‌ها با CSRF token محافظت می‌شوند؛ درخواست‌های درگ‌اند‌دراپ با هدر `X-CSRF-Token`.
- هدرهای امنیتی CSP، `X-Frame-Options`، `X-Content-Type-Options` و `Referrer-Policy` فعال هستند.
- هر کاربر فقط به پروژه‌های خودش دسترسی دارد؛ غیرعضو پاسخ ۴۰۴ می‌گیرد.
- فقط مالک پروژه می‌تواند اعضا و ستون‌ها را مدیریت کند.
- حذف کارت فقط توسط سازندهٔ همان کارت انجام می‌شود.
- کلید JWT از `.env` خوانده می‌شود و در Git نادیده گرفته می‌شود.
