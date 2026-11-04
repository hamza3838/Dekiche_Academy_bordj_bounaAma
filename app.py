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
    
    try:
        subs_res = supabase.table('access_codes').select('*').eq('student_name', student_name).execute()
        subscriptions = subs_res.data if subs_res and subs_res.data else []

        lessons = []
        if subscriptions:
            for sub in subscriptions:
                g_val = sub.get('grade') or sub.get('school_year')
                sub_val = sub.get('subject')
                m_val = sub.get('month') or sub.get('code_month')
                
                if g_val and sub_val and m_val:
                    # جلب الدروس مرتبة حسب الترتيب (lesson_order) تنازلياً أو تصاعدياً
                    l_res = supabase.table('lessons').select('*').eq('school_year', g_val).eq('subject', sub_val).eq('month', str(m_val)).order('lesson_order', desc=False).execute()
                    if l_res and l_res.data:
                        lessons.extend(l_res.data)
    except Exception as e:
        flash(f"حدث خطأ أثناء جلب الدروس: {e}", "danger")
        lessons = []

    return render_template('student_dashboard.html', student_name=student_name, subscriptions=subscriptions, lessons=lessons)

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
        month = request.form.get('month')
        week = request.form.get('week')
        title = request.form.get('title')
        video_url = request.form.get('video_url')
        pdf_url = request.form.get('pdf_url')
        
        # إضافة دعم ترتيب الدرس (lesson_order) افتراضياً 0
        try:
            lesson_order = int(request.form.get('lesson_order', 0))
        except ValueError:
            lesson_order = 0

        try:
            supabase.table('lessons').insert({
                'school_year': school_year,
                'subject': subject,
                'month': month,
                'week': week,
                'title': title,
                'video_url': video_url,
                'pdf_url': pdf_url,
                'lesson_order': lesson_order
            }).execute()
            flash("تم إضافة الدرس بنجاح!", "success")
        except Exception as e:
            flash(f"خطأ أثناء إضافة الدرس: {e}", "danger")

    lessons_data = []
    try:
        # جلب الدروس مرتبة حسب الترتيب (lesson_order)
        lessons_res = supabase.table('lessons').select('*').order('lesson_order', desc=False).execute()
        if lessons_res and lessons_res.data:
            lessons_data = lessons_res.data
    except Exception as e:
        pass

    return render_template('teacher_dashboard.html', lessons=lessons_data)

# --- مسار حذف الدرس للأستاذ ---
@app.route('/delete-lesson/<int:lesson_id>', methods=['POST'])
def delete_lesson(lesson_id):
    if not session.get('is_teacher'):
        return redirect(url_for('teacher_login'))

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('teacher_dashboard'))

    try:
        supabase.table('lessons').delete().eq('id', lesson_id).execute()
        flash("تم حذف الدرس بنجاح!", "success")
    except Exception as e:
        flash(f"خطأ أثناء حذف الدرس: {e}", "danger")

    return redirect(url_for('teacher_dashboard'))

@app.route('/admin-secret-panel-daqiche', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST' and 'password' in request.form:
        if request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
        else:
            flash("كلمة المرور غير صحيحة", "danger")

    if not session.get('is_admin'):
        return render_template('admin_login.html')

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return render_template('admin_panel.html', codes=[])

    if request.method == 'POST' and 'generate_code' in request.form:
        school_year = request.form.get('school_year')
        subject = request.form.get('subject')
        month = request.form.get('month')

        # قراءة العدد المطلوب توليده دفعة واحدة (افتراضياً 1)
        try:
            count = int(request.form.get('count', 1))
            if count < 1: count = 1
            if count > 50: count = 50  # حد أقصى في الدفعة الواحدة للأمان
        except ValueError:
            count = 1

        # تحديد تاريخ انتهاء افتراضي (بعد سنة من الآن) لتجنب خطأ expires_at
        future_date = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')

        try:
            for _ in range(count):
                random_code = "DAQ-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                supabase.table('access_codes').insert({
                    'code': random_code,
                    'grade': school_year,
                    'subject': subject,
                    'month': month,
                    'is_registered': 0,
                    'student_name': "غير محدد",
                    'phone': "0000000000",
                    'expires_at': future_date
                }).execute()
            
            flash(f"تم توليد {count} كود بنجاح!", "success")
        except Exception as e:
            flash(f"خطأ أثناء حفظ الأكواد: {e}", "danger")

    codes = []
    try:
        codes_res = supabase.table('access_codes').select('*').order('id', desc=True).execute()
        if codes_res and codes_res.data:
            codes = codes_res.data
    except Exception as e:
        pass

    return render_template('admin_panel.html', codes=codes)

# --- مسار حذف كود معين للمشرف ---
@app.route('/delete-code/<int:code_id>', methods=['POST'])
def delete_code(code_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_panel'))

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('admin_panel'))

    try:
        supabase.table('access_codes').delete().eq('id', code_id).execute()
        flash("تم حذف الكود بنجاح!", "success")
    except Exception as e:
        flash(f"خطأ أثناء حذف الكود: {e}", "danger")

    return redirect(url_for('admin_panel'))

# --- مسار الحذف الجماعي أو المختار للأكواد للمشرف ---
@app.route('/delete-selected-codes', methods=['POST'])
def delete_selected_codes():
    if not session.get('is_admin'):
        return redirect(url_for('admin_panel'))

    if not supabase:
        flash("عذراً، الاتصال بقاعدة البيانات غير متوفر حالياً.", "danger")
        return redirect(url_for('admin_panel'))

    selected_ids = request.form.getlist('code_ids')
    action_type = request.form.get('action_type')

    try:
        if action_type == 'all':
            # حذف كافة الأكواد في القاعدة
            supabase.table('access_codes').delete().gt('id', 0).execute()
            flash("تم حذف كافة الأكواد بنجاح!", "success")
        elif selected_ids:
            # حذف الأكواد المحددة فقط
            for code_id in selected_ids:
                supabase.table('access_codes').delete().eq('id', int(code_id)).execute()
            flash(f"تم حذف {len(selected_ids)} كود بنجاح!", "success")
        else:
            flash("لم يتم تحديد أي كود للحذف!", "danger")
    except Exception as e:
        flash(f"خطأ أثناء الحذف: {e}", "danger")

    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
