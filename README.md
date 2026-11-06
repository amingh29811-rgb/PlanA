# Plan A

فروشگاه قالب و افزونه‌ی وردپرس با تم سبز پسته‌ای، ساخته‌شده با Django و FastAPI.

## بخش‌ها

- `backend/`: فروشگاه (Django): محصولات، حساب کاربری، سبد خرید، سفارش، پرداخت، دانلود امن، صدور لایسنس
- `license_api/`: سرویس لایسنس (FastAPI): فعال‌سازی، اعتبارسنجی و برداشتن لایسنس از دامنه

## اجرای محلی

### فروشگاه (پورت ۸۰۰۰)

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### سرویس لایسنس (پورت ۸۰۰۱)

```bash
cd license_api
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

مستندات تعاملی API: `http://127.0.0.1:8001/docs`

## تست‌ها

```bash
cd backend && python manage.py test
cd license_api && python -m pytest -q
```

## نکته‌ها

- درگاه پرداخت فعلی **آزمایشی** است و فقط در حالت `DEBUG` کار می‌کند.
- در محیط واقعی حتماً `DJANGO_SECRET_KEY` و `DJANGO_DEBUG=0` را تنظیم کنید.
- فایل‌های فروشی در `backend/private_files/` ذخیره می‌شوند و عمداً در Git نیستند.