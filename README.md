# Moodle Dashboard

داشبورد للمهمات والكويزات والامتحانات، يشتغل على GitHub Pages ويتحدّث تلقائياً من تقويم مودل.

## الملفات

| الملف | وظيفته |
|---|---|
| `index.html` | صفحة الداشبورد (تقرأ `data.json`) |
| `data.json` | البيانات (فيها أمثلة الآن، والمزامنة تستبدلها) |
| `sync.py` | يجلب تقويم مودل ويحوّله إلى `data.json` |
| `.github/workflows/sync.yml` | يشغّل `sync.py` كل 3 ساعات |

## التشغيل خطوة بخطوة

1. أنشئ مستودع جديد على GitHub (مثلاً `moodle-dashboard`) وارفع كل الملفات، مع الحفاظ على مجلد `.github/workflows/`.
2. **تفعيل الصفحة:** Settings ← Pages ← Source: `Deploy from a branch` ← Branch: `main` / root.
   بعد دقيقة يصير الرابط: `https://USERNAME.github.io/moodle-dashboard/`
3. **رابط التقويم من مودل:** افتح Calendar ← Import or export calendars ← Export calendar ← اختر "All courses" و "Custom range" (أو Recent and next 60 days) ← Get calendar URL ← انسخ الرابط.
4. **خزّنه كسر:** في المستودع: Settings ← Secrets and variables ← Actions ← New repository secret
   - Name: `MOODLE_ICS_URL`
   - Secret: الرابط الذي نسخته
5. شغّل المزامنة أول مرة يدوياً: تبويب Actions ← Sync Moodle ← Run workflow.

> ⚠️ رابط التقويم فيه مفتاح خاص بحسابك، لا تضعه داخل الكود ولا تنشره. استخدم Secret فقط.
> وبما أن الصفحة عامة، أي شخص عنده رابطها يشوف المواعيد (لا توجد كلمات مرور فيها).

## التخصيص

- الاسم: متغير `USER_NAME` أعلى سكربت `index.html`.
- تصنيف كويز/امتحان مقابل مهمة: يعتمد على كلمات العنوان في `EXAM_WORDS` داخل `sync.py`.
- علامة ✓ على كل بطاقة تُحفظ في متصفحك فقط.
- إذا تأخرت المزامنة أكثر من 12 ساعة تتحول النقطة الخضراء إلى برتقالية.
