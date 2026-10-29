# بوردیک (Bordik) — مدیریت پروژه و وظایف تیمی

اپلیکیشن شبیه ترللو برای شرکت: هر کاربر با شماره همراه ثبت‌نام می‌کند، پروژه می‌سازد، همکاران را با شماره همراه عضو می‌کند و وظیفه‌ها را بین ستون‌ها جابه‌جا می‌کند. هر وظیفه می‌تواند چند مسئول داشته باشد.

پشته فناوری: FastAPI، Jinja2، SQLAlchemy، PostgreSQL (یا SQLite برای توسعه)، Alembic، JWT و Argon2.

## امکانات

- ثبت‌نام و ورود با شماره همراه و رمز عبور
- ورود ماندگار (تا ۳۰ روز) با تمدید خودکار جلسه، مناسب استفادهٔ روزمره روی گوشی
- پروژه (برد) با ستون‌های پیش‌فرض «برای انجام، در حال انجام، انجام‌شده»
- ساخت پروژه از طریق مودال و نوار پیشرفت هر پروژه (تعداد وظایف انجام‌شده از کل)
- ساخت، حذف و تغییر نام/نوع ستون‌ها توسط مالک پروژه
- وظیفه با عنوان، توضیحات، اولویت (کم/معمولی/زیاد/فوری)، سررسید (تاریخ مشخص یا تعداد روز) و چند مسئول
- صفحهٔ «وظایف من» با مرتب‌سازی بر اساس اولویت و نزدیک‌ترین سررسید
- انتخاب اجباری مسئول هنگام ساخت وظیفه و ارسال نوتیفیکیشن برای مسئولان (از طریق ربات روبیکا)
- رنگ اختصاصی هر پروژه برای تفکیک بصری پروژه‌ها (قابل ویرایش) و تگ تعداد وظایف هر شخص روی کارت پروژه
- تاریخ‌ها و دیت‌پیکر جلالی (شمسی) در رابط وب
  (دیت‌پیکر از کتابخانهٔ [JalaliDatePicker](https://github.com/majidh1/JalaliDatePicker) با لایسنس MIT، به‌صورت لوکال در `task_manager/static/vendor/jalalidatepicker/`)
- نمایش «چند روز مانده / امروز / چند روز تأخیر» روی وظیفه‌ها
- ثبت خودکار «تاریخ انجام» وقتی وظیفه وارد ستون انجام‌شده می‌شود (تأخیر دیگر حساب نمی‌شود)
- حذف وظیفه فقط توسط سازندهٔ همان وظیفه (مالک پروژه فقط برای وظیفه‌های بدون سازنده)
- جابه‌جایی وظیفه بین ستون‌ها با درگ‌اند‌دراپ و ترتیب دلخواه
- عضویت با شماره همراه؛ اگر کاربر ثبت‌نام نکرده باشد، دعوت در انتظار می‌ماند و پس از ثبت‌نام خودکار فعال می‌شود (بدون نیاز به پیامک)
- نقش مالک و عضو با دسترسی‌های جداگانه
- رابط وب فارسی و راست‌به‌چپ + REST API مستند در `/docs`
- ربات روبیکا برای دیدن لیست وظایف و افزودن وظیفه جدید (اتصال با شماره همراه)
- فونت وزیرمتن به‌صورت لوکال همراه پروژه است (بدون نیاز به اینترنت)
- **PWA**: قابل نصب روی موبایل و دسکتاپ («افزودن به صفحه اصلی»)، اجرای تمام‌صفحه، آیکون اختصاصی و صفحهٔ آفلاین
  (فایل‌های `manifest.webmanifest`، `sw.js`، `pwa.js` و آیکون‌ها در `task_manager/static/icons/`)

## نصب روی موبایل (PWA)

نرم‌افزار به‌صورت PWA کار می‌کند؛ کافی است سایت را در مرورگر موبایل باز کنی:

- روی گوشی، بعد از باز کردن برنامه یک **پاپ‌آپ نصب** نمایش داده می‌شود که تا وقتی برنامه را نصب نکرده‌ای
  دوباره ظاهر می‌شود («بعداً» فقط همان بازدید را رد می‌کند). بعد از نصب، پاپ‌آپ دیگر نمایش داده نمی‌شود و
  هیچ دکمهٔ نصب دیگری در برنامه نیست.
- منوی هدر روی موبایل با دکمهٔ «منو» باز می‌شود (پروژه‌ها، وظایف من، اعلان‌ها، نام کاربر و خروج).
- برای اینکه ظاهر برنامه روی موبایل به‌هم نریزد، زوم صفحه در حالت نصب/موبایل محدود شده است.
- **اندروید (Chrome/Edge)**: در پاپ‌آپ دکمهٔ «نصب برنامه» را بزن، یا از منوی مرورگر گزینهٔ «Install app» /
  «افزودن به صفحهٔ اصلی» را انتخاب کن.
- **آیفون (Safari)**: پاپ‌آپ مرحله‌به‌مرحله راهنمایی می‌کند؛ دکمهٔ «اشتراک‌گذاری» را بزن و
  «Add to Home Screen» را انتخاب کن. (سافاری رویداد نصب خودکار را پشتیبانی نمی‌کند.)
- بعد از نصب، برنامه تمام‌صفحه و بدون نوار آدرس باز می‌شود و آیکون «بوردیک» روی صفحهٔ اصلی قرار می‌گیرد.

نکته‌ها:

- Service worker فقط با **HTTPS** (یا `localhost`) فعال می‌شود؛ برای همین روی سرور از دامنهٔ HTTPS استفاده کن
  (بخش «HTTPS با Caddy» در همین فایل).
- صفحات محتوا همیشه از سرور خوانده می‌شوند و کش نمی‌شوند؛ فقط فایل‌های استاتیک کش می‌شوند و اگر اینترنت قطع باشد
  صفحهٔ «اتصال برقرار نشد» با دکمهٔ تلاش دوباره نمایش داده می‌شود.
- برای بی‌اعتبار شدن کش مرورگر بعد از هر تغییر ظاهری، مقدار `ASSET_VERSION` در `task_manager/ui.py` را یکی زیاد کن.

اگر آیکون‌ها را تغییر دادی، دوباره بساز (بدون هیچ کتابخانهٔ بیرونی):

```powershell
.\.venv\Scripts\python.exe tools\generate_pwa_icons.py
```

## ورود ماندگار روی گوشی

- با تیک «مرا به خاطر بسپار» (به‌صورت پیش‌فرض روشن است) کوکی ورود تا **`SESSION_DAYS`** روز (پیش‌فرض: ۳۰ روز)
  معتبر می‌ماند؛ پس روی گوشی هر بار لازم نیست دوباره وارد شوی.
- جلسه **کشسان (sliding)** است: هر بار صفحه‌ای باز کنی و کمتر از نیمی از عمر جلسه مانده باشد، خودکار تمدید می‌شود؛
  یعنی تا وقتی برنامه را باز می‌کنی، جلسه تمام نمی‌شود و فقط بعد از ۳۰ روز بی‌کاری باید دوباره وارد شوی.
- اگر تیک را برداری، کوکی «جلسه‌ای» می‌شود و با بستن کامل مرورگر پاک می‌شود.
- برای تغییر مدت، در `.env` مقدار `SESSION_DAYS` را عوض کن (بین ۱ تا ۳۶۵). توکن API (`ACCESS_TOKEN_EXPIRE_MINUTES`)
  جداست و فقط برای درخواست‌های REST استفاده می‌شود.

## عیب‌یابی روی گوشی

### «ERR_CONNECTION_TIMEOUT» یا «سایت در دسترس نیست»

این خطا یعنی گوشی **حتی به سرور هم وصل نمی‌شود** (مشکل شبکه/اجراست، نه کد). به ترتیب چک کن:

1. روشن بودن سرور روی خود ماشین:
   ```bash
   curl http://127.0.0.1:8000/health     # باید {"status":"ok"} بدهد
   ```
2. **آدرس درست گوشی**: باید IP شبکهٔ محلی ماشین باشد، نه `127.0.0.1`. IP را با این دستور پیدا کن:
   ```powershell
   .\tools\lan-serve.ps1        # هم IP را چاپ می‌کند هم سرور را روی 0.0.0.0 بالا می‌آورد
   ```
   یا برای Docker، پورت را منتشر کن (فایل `docker-compose.yml` به‌تنهایی پورت را منتشر **نمی‌کند**):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d --build
   docker compose ps            # باید 0.0.0.0:8000->8000/tcp را ببینی
   ```
3. **فایروال ویندوز** (یک‌بار با دسترسی Administrator):
   ```powershell
   New-NetFirewallRule -DisplayName "Bordik 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   ```
4. **هم‌شبکه بودن**: گوشی و سرور باید روی یک Wi-Fi باشند (دادهٔ همراه/شبکهٔ مهمان کار نمی‌کند) و IP ماشین
   عوض نشده باشد (DHCP) — برای همین IP ثابت یا نام دامنه بهتر است.
5. اگر پشت پروکسی/دامنه هستی: `docker compose logs --tail=50 app` را ببین؛ اگر هیچ درخواستی از گوشی ثبت
   نشده، مشکل همان لایهٔ قبل از برنامه (DNS/TLS/پروکسی) است.

### «از خود گوشی این‌ها را باز کن»

- `http://<آدرس-سرور>:8000/health` → باید `{"status":"ok"}` ببینی.
- `http://<آدرس-سرور>:8000/diag` → خروجی JSON نشان می‌دهد درخواست گوشی با چه پروتکلی رسیده، کدام کوکی‌ها
  رسیده‌اند، کوکی `Secure` روی این پروتکل ست می‌شود یا نه، و دیتابیس سالم است یا نه. همین خروجی را برای
  عیب‌یابی بفرست.

### صفحهٔ سفید در آیکون نصب‌شده

- تا وقتی گوشی به سرور وصل نشود، سرویس‌ورکر صفحهٔ «اتصال برقرار نشد» را نشان می‌دهد (و اگر آن هم نبود، یک
  صفحهٔ سادم با پیام فارسی). با درست شدن اتصال، صفحه عادی برمی‌گردد.
- اگر بعد از رفع مشکل، نسخهٔ قدیمی را دیدی: میان‌بر را پاک کن و دوباره اضافه کن، یا در Chrome
  `تنظیمات سایت → Clean data` بزن تا Service Worker قدیمی پاک شود (کش با `ASSET_VERSION` و
  `CACHE_NAME` در `sw.js` نسخه‌بندی می‌شود).

### صفحهٔ ورود می‌آید ولی وارد نمی‌شوم

- در تنظیمات مرورگر گوشی، کوکی‌ها/سایت‌دیتا را برای این دامنه بلاک نکرده باشی.
- برای نصب PWA و اعلان مرورگر به **HTTPS** نیاز داری؛ روی `http://<ip>` خود برنامه کار می‌کند ولی نصب و
  اعلان فعال نمی‌شود.
- `COOKIE_SECURE` فقط به‌عنوان «سایت روی HTTPS است» در نظر گرفته می‌شود؛ فلگ `Secure` بر اساس پروتکل واقعی هر
  درخواست ست می‌شود تا دسترسی با HTTP (آزمایش در شبکهٔ محلی) هم کار کند.

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
| GET | `/api/my/tasks` | وظایف من، مرتب بر اساس اولویت و سررسید |
| PATCH | `/api/projects/{id}` | ویرایش پروژه (مالک) |
| DELETE | `/api/projects/{id}` | حذف پروژه (مالک) |
| GET | `/api/projects/{id}/members` | اعضا |
| POST | `/api/projects/{id}/members` | افزودن عضو/دعوت با شماره |
| DELETE | `/api/projects/{id}/members/{user_id}` | حذف عضو (مالک) |
| POST | `/api/projects/{id}/columns` | ساخت ستون (مالک) |
| PATCH | `/api/projects/{id}/columns/{column_id}` | ویرایش ستون (مالک) |
| DELETE | `/api/projects/{id}/columns/{column_id}` | حذف ستون خالی (مالک) |
| POST | `/api/projects/{id}/cards` | ساخت وظیفه |
| GET | `/api/projects/{id}/cards/{card_id}` | یک وظیفه |
| PATCH | `/api/projects/{id}/cards/{card_id}` | ویرایش وظیفه |
| PUT | `/api/projects/{id}/cards/{card_id}/assignees` | تعیین مسئولان |
| POST | `/api/projects/{id}/cards/{card_id}/move` | جابه‌جایی وظیفه |
| DELETE | `/api/projects/{id}/cards/{card_id}` | حذف وظیفه (فقط سازنده) |

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

> نسخهٔ پروداکشن `docker-compose.yml` پورت ۸۰۰۰ را منتشر نمی‌کند (`expose` است) و باید یک reverse proxy (مثل Caddy/Nginx) جلوی آن باشد؛ `COOKIE_SECURE=true` است و uvicorn با `--proxy-headers --forwarded-allow-ips` اجرا می‌شود.

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

## سررسید وظیفه

هر وظیفه می‌تواند یکی از این دو را داشته باشد:

- `due_date`: تاریخ میلادی مثل `2030-01-02`
- `due_in_days`: تعداد روز از امروز

در پاسخ API فیلد محاسبه‌شدهٔ `days_remaining` و `due_date_jalali` هم برمی‌گردد. وقتی وظیفه وارد ستون «انجام‌شده» شود، تاریخ انجام در `completed_at` ثبت می‌شود و دیگر تأخیر محاسبه نمی‌شود. در رابط وب تاریخ‌ها جلالی هستند و دیت‌پیکر جلالی به‌صورت آفلاین همراه پروژه عرضه شده است (بدون نیاز به اینترنت یا CDN). با گزینهٔ «حذف سررسید» می‌توانی تاریخ را پاک کنی.

## ربات روبیکا

ربات به‌صورت **Polling** داخل خود اپ اجرا می‌شود و نیازی به وبهوک و دامنه ندارد.

فعال‌سازی در `.env`:
```env
RUBIKA_ENABLED=true
RUBIKA_BOT_TOKEN=توکن-ربات
RUBIKA_API_BASE=https://botapi.rubika.ir/v3
RUBIKA_POLL_INTERVAL_SECONDS=3
```
سپس اپ را ری‌استارت کن (`docker compose up -d` یا `Restart-Service Bordik`).

دستورات ربات:

| دستور | کار |
| --- | --- |
| `/link 09121234567` | وصل‌کردن این چت به حساب بوردیک (باید قبلاً در سایت با همین شماره ثبت‌نام کرده باشی) |
| `/tasks` | لیست وظایف من در همهٔ پروژه‌ها |
| `/add نام پروژه \| عنوان وظیفه` | ساخت وظیفه جدید در ستون اول پروژه |
| `/done 12` | انجام‌شده‌کردن وظیفه شماره ۱۲ |
| `/help` | راهنما |

نکته‌ها:
- لینک فقط با **شماره همراه** انجام می‌شود؛ اگر شماره در بوردیک ثبت نشده باشد، ربات همان را اعلام می‌کند.
- نام متدهای API روبیکا ممکن است بین نسخه‌ها متفاوت باشد؛ با `RUBIKA_SEND_METHOD` و `RUBIKA_UPDATES_METHOD` قابل تغییرند (پیش‌فرض: `sendMessage` و `getUpdates`).
- اگر توکن نداری، `RUBIKA_ENABLED=false` بگذار؛ ساختار و جدول‌ها آماده می‌مانند و بعداً فقط توکن را پر می‌کنی.

## اولویت و نوتیفیکیشن

- هر وظیفه یک `priority` دارد: `low`, `normal`, `high`, `urgent`.
- در صفحهٔ «وظایف من» وظیفه‌ها اول بر اساس اولویت (فوری → زیاد → معمولی → کم) و بعد بر اساس نزدیک‌ترین سررسید مرتب می‌شوند.
- هنگام ساخت وظیفه، انتخاب **حداقل یک مسئول** در فرم الزامی است. (اگر از API استفاده کنی و مسئولی نفرستی، سازندهٔ وظیفه به‌عنوان مسئول پیش‌فرض ثبت می‌شود.)
- پس از ساخته‌شدن وظیفه، برای مسئولانی که حساب روبیکای‌شان وصل است پیام نوتیفیکیشن فرستاده می‌شود (فقط وقتی `RUBIKA_ENABLED=true` باشد).
- صفحهٔ «وظایف من» هم در رابط وب (`/my-tasks`) و هم در API (`/api/my/tasks`) در دسترس است و فیلترهای `scope=mine|all` و `include_done` دارد (به‌صورت پیش‌فرض فقط انجام‌نشده‌ها).

## رنگ پروژه

هر پروژه یکی از رنگ‌های آمادهٔ پالت را می‌گیرد (`blue, green, purple, orange, rose, teal, slate`). رنگ در وظیفه پروژه، هدر برد و نوار پیشرفت استفاده می‌شود. از API با فیلد `color` و در رابط وب با انتخابگر رنگ در مودال ساخت پروژه تنظیم می‌شود.

## اعلان مرورگر

- هنگام سپردن هر وظیفه، برای هر مسئول یک اعلان داخلی ذخیره می‌شود.
- در نوار بالا دکمهٔ «اعلان‌ها» با شمارندهٔ خوانده‌نشده‌ها هست.
- بار اول روی «فعال‌سازی اعلان مرورگر» بزن و مجوز را بده؛ بعد از آن هر اعلان جدید به‌صورت نوتیفیکیشن مرورگر نمایش داده می‌شود.
- صفحه هر ۲۰ ثانیه اعلان‌ها را بررسی می‌کند (بدون نیاز به سرویس Push و کلید VAPID).
- اعلان مرورگر فقط روی بستر امن (HTTPS) یا `localhost` کار می‌کند؛ اگر سایت را با `http://IP-سرور:8000` باز کنی مرورگر اجازه نمی‌دهد و پیام راهنما نمایش داده می‌شود. پشت Caddy/SSL مشکلی نیست.
- نقاط داخلی: `GET /ui/notifications/feed` و `POST /ui/notifications/read`.

## امنیت

- رمز عبور با Argon2 هش می‌شود.
- API فقط Bearer token می‌پذیرد؛ کوکی نشست مخصوص رابط وب است.
- فرم‌ها با CSRF token محافظت می‌شوند؛ درخواست‌های درگ‌اند‌دراپ با هدر `X-CSRF-Token`.
- هدرهای امنیتی CSP، `X-Frame-Options`، `X-Content-Type-Options` و `Referrer-Policy` فعال هستند.
- هر کاربر فقط به پروژه‌های خودش دسترسی دارد؛ غیرعضو پاسخ ۴۰۴ می‌گیرد.
- فقط مالک پروژه می‌تواند اعضا و ستون‌ها را مدیریت کند.
- حذف وظیفه فقط توسط سازندهٔ همان وظیفه انجام می‌شود.
- کلید JWT از `.env` خوانده می‌شود و در Git نادیده گرفته می‌شود.
