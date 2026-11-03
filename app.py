from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dar_daqiche_secret_key_2026")

# قراءة وتنظيف متغيرات البيئة بسلامة تامة
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

# حماية التطبيق من الانهيار إذا كانت المتغيرات فارغة أو المفتاح غير صالح أثناء الإقلاع
if not SUPABASE_URL or not SUPABASE_URL.startswith("http"):
    print("⚠️ تحذير: SUPABASE_URL غير مضبوط بشكل صحيح في البيئة، يتم استخدام رابط مؤقت لتفادي التوقف.")
    SUPABASE_URL = "https://placeholder.supabase.co"
    SUPABASE_KEY = "placeholder_key"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"⚠️ تحذير: حدث خطأ أثناء تهيئة عميل Supabase: {e}")
    supabase = None

# كلمات المرور
ADMIN_PASSWORD = "admin_secure_2026"
TEACHER_PASSWORD = "teacher_password_2026"

@app.route('/')
def home():
    return render_template('index.html')

# --- بوابة التلميذ (إدخال الكود أو الدخول بالاسم والهاتف) ---
@app.route('/student-login', methods=['POST'])
def student_login():
    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('home'))

    action = request.form.get('action')
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')

    if action == 'login':
        # التحقق من وجود التلميذ في جدول الأكواد المستعملة
        res = supabase.table('access_codes').select('*').eq('phone', phone).eq('student_name', full_name).execute()
        if res.data:
            session['student_name'] = full_name
            session['phone'] = phone
            return redirect(url_for('student_dashboard'))
        else:
            flash("البيانات غير صحيحة أو لم تقم بتفعيل كود من قبل.", "danger")
            return redirect(url_for('home'))

    elif action == 'redeem':
        code_text = request.form.get('code')
        # البحث عن الكود في قاعدة البيانات والتأكد أنه غير مستعمل
        code_res = supabase.table('access_codes').select('*').eq('code', code_text).eq('is_used', False).execute()
        
        if not code_res.data:
            flash("الكود غير صالح أو تم استخدامه مسبقاً!", "danger")
            return redirect(url_for('home'))
        
        code_data = code_res.data[0]

        # تحديث الكود ليرتبط بالتلميذ ويصبح مستخدماً
        supabase.table('access_codes').update({
            'student_name': full_name,
            'phone': phone,
            'is_used': True
        }).eq('id', code_data['id']).execute()

        session['student_name'] = full_name
        session['phone'] = phone
        flash("تم تفعيل اشتراكك بنجاح!", "success")
        return redirect(url_for('student_dashboard'))

# --- لوحة تحكم التلميذ ---
@app.route('/student-dashboard')
def student_dashboard():
    if 'student_name' not in session:
        return redirect(url_for('home'))

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('home'))

    student_name = session['student_name']
    
    # جلب جميع اشتراكات وباقات التلميذ الفعالة
    subs_res = supabase.table('access_codes').select('*').eq('student_name', student_name).execute()
    subscriptions = subs_res.data

    # جلب الدروس المطابقة للمواد والسنوات التي اشتراها التلميذ
    lessons = []
    if subscriptions:
        for sub in subscriptions:
            l_res = supabase.table('lessons').select('*').eq('school_year', sub.get('grade')).eq('subject', sub.get('subject')).eq('month', sub.get('month')).execute()
            lessons.extend(l_res.data)

    return render_template('student_dashboard.html', student_name=student_name, subscriptions=subscriptions, lessons=lessons)

# --- بوابة الأستاذ ---
@app.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        if request.form.get('password') == TEACHER_PASSWORD:
            session['is_teacher'] = True
            return redirect(url_for('teacher_dashboard'))
        flash("كلمة مرور الأستاذ غير صحيحة", "danger")
    return render_template('teacher_login.html')

@app.route('/teacher-dashboard', methods=['GET', 'POST'])
def teacher_dashboard():
    if not session.get('is_teacher'):
        return redirect(url_for('teacher_login'))

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return render_template('teacher_dashboard.html', lessons=[])

    if request.method == 'POST':
        school_year = request.form.get('school_year')
        subject = request.form.get('subject')
        month = request.form.get('month')
        week = request.form.get('week')
        title = request.form.get('title')
        video_url = request.form.get('video_url')
        pdf_url = request.form.get('pdf_url')

        try:
            supabase.table('lessons').insert({
                'school_year': school_year,
                'subject': subject,
                'month': month,
                'week': week,
                'title': title,
                'video_url': video_url,
                'pdf_url': pdf_url
            }).execute()
            flash("تم إضافة الدرس بنجاح!", "success")
        except Exception as e:
            flash(f"خطأ أثناء إضافة الدرس: {e}", "danger")

    lessons_data = []
    try:
        lessons_res = supabase.table('lessons').select('*').order('created_at', desc=True).execute()
        if lessons_res and lessons_res.data:
            lessons_data = lessons_res.data
    except Exception as e:
        print(f"⚠️ ملاحظة أثناء جلب الدروس: {e}")

    return render_template('teacher_dashboard.html', lessons=lessons_data)

# --- لوحة المشرف المباشرة والآمنة (بدون الحاجة لملفات قوالب خارجية) ---
@app.route('/admin-secret-panel-daqiche', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST' and 'password' in request.form:
        if request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
        else:
            flash("كلمة المرور غير صحيحة", "danger")

    if not session.get('is_admin'):
        return '''
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>تسجيل دخول المشرف - أكاديمية دقيش</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tailwindcss@3.4.17/dist/tailwind.min.css">
            <style>body { font-family: Tahoma, sans-serif; background: #101e2a; color: #f7f3ea; }</style>
        </head>
        <body class="flex items-center justify-center min-h-screen">
            <div class="bg-[#192b39] p-8 rounded-2xl border border-[#e9bd68]/30 max-w-md w-full shadow-2xl text-center">
                <h2 class="text-2xl font-bold mb-6 text-[#e9bd68]">لوحة تحكم المشرف</h2>
                <form method="POST" class="space-y-4">
                    <input type="password" name="password" placeholder="أدخل كلمة مرور المشرف" required class="w-full p-3 rounded-xl bg-[#101e2a] border border-[#617586] text-white outline-none focus:border-[#e9bd68]">
                    <button type="submit" class="w-full py-3 bg-[#e9bd68] text-[#101e2a] font-bold rounded-xl hover:brightness-110 transition">دخول</button>
                </form>
                <div class="mt-4"><a href="/" class="text-sm text-[#b8c7d0] hover:underline">العودة للرئيسية</a></div>
            </div>
        </body>
