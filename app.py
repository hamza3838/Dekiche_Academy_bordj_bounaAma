from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client
import os
import datetime
import random
import string
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dar_daqiche_secret_key_2026")

# --- بيانات الاتصال الرسمية والصحيحة لقاعدة بيانات Supabase ---
SUPABASE_URL = "https://dobbzqbdlpzfqsewcjoz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRvYmJ6cWJkbHB6ZnFzZXdjam96Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM1NjQyMDUsImV4cCI6MjEwOTE0MDIwNX0.Rz_4hNCixS9-FjiAs54Xu0xu0qhhteNly3SVgpHn7tw"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ تم الاتصال بقاعدة البيانات بنجاح!")
except Exception as e:
    print(f"❌ خطأ في الاتصال: {e}")
    supabase = None

ADMIN_PASSWORD = "admin_secure_2026"
TEACHER_PASSWORD = "teacher_password_2026"

# --- دالة التحقق من صحة رقم الهاتف الجزائري (10 أرقام وتبدأ بـ 05, 06, 07) ---
def is_valid_phone(phone):
    if not phone:
        return False
    return bool(re.match(r'^0[567]\d{8}$', phone))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/student-login', methods=['POST'])
def student_login():
    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('home'))

    action = request.form.get('action')
    full_name = request.form.get('full_name')
    phone = request.form.get('phone', '').strip()

    # التحقق من صحة رقم الهاتف قبل متابعة أي عملية
    if not is_valid_phone(phone):
        flash("رقم الهاتف غير صحيح! يجب أن يتكون من 10 أرقام ويبدأ بـ 05، 06 أو 07 دون حروف أو رموز.", "danger")
        return redirect(url_for('home'))

    if action == 'login':
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
        # البحث عن الكود غير المستخدم (is_registered = 0)
        code_res = supabase.table('access_codes').select('*').eq('code', code_text).eq('is_registered', 0).execute()
        
        if not code_res.data:
            flash("الكود غير صالح أو تم استخدامه مسبقاً!", "danger")
            return redirect(url_for('home'))
        
        code_data = code_res.data[0]

        # تحديث الكود بالبيانات الحقيقية للتلميذ وتعيينه كمستخدم (is_registered = 1)
        supabase.table('access_codes').update({
            'student_name': full_name,
            'phone': phone,
            'is_registered': 1
        }).eq('id', code_data['id']).execute()

        session['student_name'] = full_name
        session['phone'] = phone
        flash("تم تفعيل اشتراكك بنجاح!", "success")
        return redirect(url_for('student_dashboard'))

@app.route('/student-dashboard')
def student_dashboard():
    if 'student_name' not in session:
        return redirect(url_for('home'))

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('home'))

    student_name = session['student_name']
    
    subscriptions = []
    lessons = []
    try:
        subs_res = supabase.table('access_codes').select('*').eq('student_name', student_name).execute()
        subscriptions = subs_res.data if subs_res and subs_res.data else []

        if subscriptions:
            for sub in subscriptions:
                g_val = sub.get('grade') or sub.get('school_year')
                sub_val = sub.get('subject')
                m_val = sub.get('month') or sub.get('code_month')
                
                if g_val and sub_val and m_val:
                    # جلب الدروس مرتبة حسب الترتيب (lesson_order) مع دعم الأشهر الرقمية
                    l_res = supabase.table('lessons').select('*').eq('school_year', g_val).eq('subject', sub_val).eq('month', str(m_val)).order('lesson_order', desc=False).execute()
                    if l_res and l_res.data:
                        lessons.extend(l_res.data)
    except Exception as e:
        flash(f"حدث خطأ أثناء جلب الدروس: {e}", "danger")
        lessons = []

    # تنظيم الدروس حسب طبيعة المادة (رياضيات: وضعيات انطلاقية، بقية المواد: مقاطع ثم أسابيع)
    organized_data = {}
    if subscriptions:
        current_subject = subscriptions[0].get('subject') # أو بناءً على المادة المختارة
        # للتسهيل، سنصنف بناءً على المادة الأولى أو نجعلها مرنة لكل المادة المعروضة
        for lesson in lessons:
            subject = lesson.get('subject')
            if subject == 'الرياضيات':
                situation = lesson.get('unit') or 'الوضعية الانطلاقية العامة'
                if situation not in organized_data:
                    organized_data[situation] = []
                organized_data[situation].append(lesson)
            else:
                unit = lesson.get('unit') or 'مقطع عام'
                week = lesson.get('week') or 'الأسبوع الأول'
                if unit not in organized_data:
                    organized_data[unit] = {}
                if week not in organized_data[unit]:
                    organized_data[unit][week] = []
                organized_data[unit][week].append(lesson)

    return render_template('student_dashboard.html', student_name=student_name, subscriptions=subscriptions, lessons=lessons, organized_data=organized_data)

# --- مسار تفعيل كود الشهر الجديد من داخل حساب التلميذ ---
@app.route('/redeem-code', methods=['POST'])
def redeem_code():
    if 'student_name' not in session:
        return redirect(url_for('home'))

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('student_dashboard'))

    code_text = request.form.get('code')
    student_name = session['student_name']
    phone = session['phone']

    code_res = supabase.table('access_codes').select('*').eq('code', code_text).eq('is_registered', 0).execute()
    
    if not code_res.data:
        flash("الكود غير صالح أو تم استخدامه مسبقاً!", "danger")
        return redirect(url_for('student_dashboard'))
    
    code_data = code_res.data[0]

    supabase.table('access_codes').update({
        'student_name': student_name,
        'phone': phone,
        'is_registered': 1
    }).eq('id', code_data['id']).execute()

    flash("تم تفعيل اشتراك الشهر الجديد بنجاح!", "success")
    return redirect(url_for('student_dashboard'))

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
        unit = request.form.get('unit')  # المقطع التعليمي أو الوضعية الانطلاقية
        month = request.form.get('month')  # الشهر بنظام الأرقام (مثل الشهر 1)
        week = request.form.get('week')
        title = request.form.get('title')
        video_url = request.form.get('video_url')
        pdf_url = request.form.get('pdf_url')
        
        try:
            lesson_order = int(request.form.get('lesson_order', 0))
        except ValueError:
            lesson_order = 0

        try:
            supabase.table('lessons').insert({
                'school_year': school_year,
                'subject': subject,
                'unit': unit,
                'month': month,
                'week': week,
                'title': title,
                'video_url': video_url,
                'pdf_url': pdf_url,
                'lesson_order': lesson_order
            }).execute()
            flash("تم إضافة الدرس أو التمارين بنجاح!", "success")
        except Exception as e:
            flash(f"خطأ أثناء إضافة الدرس: {e}", "danger")

    lessons_data = []
    try:
        lessons_res = supabase.table('lessons').select('*').order('lesson_order', desc=False).execute()
        if lessons_res and lessons_res.data:
            lessons_data = lessons_res.data
    except Exception as e:
        pass

    return render_template('teacher_dashboard.html', lessons=lessons_data)

# --- مسار تعديل الدرس للأستاذ ---
@app.route('/edit-lesson/<int:lesson_id>', methods=['GET', 'POST'])
def edit_lesson(lesson_id):
    if not session.get('is_teacher'):
        return redirect(url_for('teacher_login'))

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'GET':
        try:
            res = supabase.table('lessons').select('*').eq('id', lesson_id).execute()
            if res.data:
                lesson = res.data[0]
                return render_template('edit_lesson.html', lesson=lesson)
            else:
                flash("الدرس غير موجود.", "danger")
                return redirect(url_for('teacher_dashboard'))
        except Exception as e:
            flash(f"خطأ أثناء جلب الدرس: {e}", "danger")
            return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        school_year = request.form.get('school_year')
        subject = request.form.get('subject')
        unit = request.form.get('unit')
        month = request.form.get('month')
        week = request.form.get('week')
        title = request.form.get('title')
        video_url = request.form.get('video_url')
        pdf_url = request
