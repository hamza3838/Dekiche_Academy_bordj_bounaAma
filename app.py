from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.secret_key = 'dekiche_academy_secret_key_2026'

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

# 1. واجهة الدخول الذكية
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        action = request.form.get('action')
        
        # دخول التلميذ بكود جديد
        if action == 'code_login':
            code = request.form.get('code').strip()
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM access_codes WHERE code = %s", (code,))
            student = cur.fetchone()
            cur.close()
            conn.close()
            
            if student:
                session['student_name'] = student['student_name'] or "تلميذ"
                session['grade'] = student['grade']
                session['phone'] = student.get('phone', '')
                return redirect(url_for('student_dashboard'))
            else:
                error = "الكود غير صحيح أو غير مفعل."
                
        # دخول التلميذ السابق بالاسم ورقم الهاتف
        elif action == 'phone_login':
            name = request.form.get('student_name').strip()
            phone = request.form.get('phone').strip()
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM access_codes WHERE student_name = %s AND phone = %s", (name, phone))
            student = cur.fetchone()
            cur.close()
            conn.close()
            
            if student:
                session['student_name'] = student['student_name']
                session['grade'] = student['grade']
                session['phone'] = student['phone']
                return redirect(url_for('student_dashboard'))
            else:
                error = "بيانات الدخول غير مطابقة أو لم يتم التسجيل مسبقاً."
                
        # دخول الأستاذ برمز سري
        elif action == 'teacher_login':
            teacher_pass = request.form.get('teacher_pass').strip()
            if teacher_pass == "AdminDekiche2026":
                session['is_teacher'] = True
                return redirect(url_for('admin_dashboard'))
            else:
                error = "رمز دخول الأستاذ غير صحيح."

    return render_template('login.html', error=error)

# 2. لوحة تحكم الأستاذ
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('is_teacher'):
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        # إضافة درس جديد
        if form_type == 'add_lesson':
            title = request.form.get('title')
            grade = request.form.get('grade')
            subject = request.form.get('subject')
            desc = request.form.get('description')
            order_idx = request.form.get('order_index', 0)
            lesson_month = request.form.get('lesson_month', 1)
            
            cur.execute(
                "INSERT INTO lessons (title, grade, subject, description, order_index, lesson_month) VALUES (%s, %s, %s, %s, %s, %s)",
                (title, grade, subject, desc, order_idx, lesson_month)
            )
            conn.commit()
            
        # إضافة كود جديد
        elif form_type == 'add_code':
            code = request.form.get('code').strip()
            grade = request.form.get('grade')
            code_month = request.form.get('code_month', 1)
            
            cur.execute(
                "INSERT INTO access_codes (code, grade, code_month) VALUES (%s, %s, %s)",
                (code, grade, code_month)
            )
            conn.commit()
            
        # تحديث ترتيب الدرس
        elif form_type == 'update_order':
            lesson_id = request.form.get('lesson_id')
            new_order = request.form.get('order_index')
            cur.execute("UPDATE lessons SET order_index = %s WHERE id = %s", (new_order, lesson_id))
            conn.commit()

    cur.execute("SELECT * FROM lessons ORDER BY lesson_month ASC, order_index ASC, id DESC")
    lessons = cur.fetchall()
    
    cur.execute("SELECT * FROM access_codes ORDER BY id DESC")
    codes = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('admin.html', lessons=lessons, codes=codes)

# 3. فضاء التلميذ الذكي
@app.route('/student', methods=['GET', 'POST'])
def student_dashboard():
    if not session.get('student_name'):
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    message = None
    if request.method == 'POST':
        new_code = request.form.get('new_code').strip()
        cur.execute("SELECT * FROM access_codes WHERE code = %s", (new_code,))
        found = cur.fetchone()
        
        if found:
            cur.execute(
                "UPDATE access_codes SET student_name = %s, phone = %s WHERE code = %s", 
                (session['student_name'], session.get('phone'), new_code)
            )
            conn.commit()
            message = f"تم تفعيل اشتراك الشهر ({found.get('code_month')}) بنجاح!"
        else:
            message = "الكود الجديد غير صالح أو غير موجود."

    grade = session.get('grade')
    student_name = session.get('student_name')

    # جلب الشهور المفعلة للطالب
    cur.execute("SELECT DISTINCT code_month FROM access_codes WHERE student_name = %s AND student_name IS NOT NULL", (student_name,))
    records = cur.fetchall()
    unlocked_months = [r['code_month'] for r in records if r['code_month'] is not None]
    
    if not unlocked_months:
        unlocked_months = [1]

    # جلب دروس الشهور المسموح بها فقط
    cur.execute(
        "SELECT * FROM lessons WHERE grade = %s AND lesson_month = ANY(%s) ORDER BY lesson_month ASC, order_index ASC", 
        (grade, unlocked_months)
    )
    lessons = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('student.html', lessons=lessons, message=message, unlocked_months=unlocked_months)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
