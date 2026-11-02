from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import random
import string
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# الاتصال بقاعدة البيانات (Supabase PostgreSQL)
def get_db_connection():
    conn = psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    return conn

# توليد أكواد عشوائية دفعة واحدة
def generate_random_codes(count=10, prefix="HAMZA"):
    codes = []
    for _ in range(count):
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        codes.append(f"{prefix}-{suffix}")
    return codes

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # جلب جميع الدروس منظمة
    cur.execute("SELECT * FROM lessons ORDER BY grade, subject, lesson_month, order_index")
    lessons = cur.fetchall()
    
    # جلب التلاميذ المسجلين
    cur.execute("SELECT * FROM access_codes WHERE student_name IS NOT NULL ORDER BY created_at DESC")
    students = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('admin.html', lessons=lessons, students=students)

@app.route('/admin/add_lesson', methods=['POST'])
def add_lesson():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    title = request.form['title']
    youtube_url = request.form['youtube_url']
    grade = request.form['grade']       # السنة الدراسية (مثلاً: الخامسة ابتدائي)
    subject = request.form['subject']   # المادة (مثلاً: لغة عربية، رياضيات)
    lesson_month = int(request.form['lesson_month'])
    order_index = int(request.form.get('order_index', 0))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO lessons (title, youtube_url, grade, subject, lesson_month, order_index) VALUES (%s, %s, %s, %s, %s, %s)",
        (title, youtube_url, grade, subject, lesson_month, order_index)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    flash("تم إضافة الدرس بنجاح!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/generate_batch_codes', methods=['POST'])
def generate_batch_codes():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    code_month = int(request.form['code_month'])
    count = int(request.form['count'])
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    new_codes = generate_random_codes(count=count, prefix=f"M{code_month}")
    for code in new_codes:
        cur.execute(
            "INSERT INTO access_codes (code, code_month, is_used) VALUES (%s, %s, FALSE)",
            (code, code_month)
        )
    conn.commit()
    cur.close()
    conn.close()
    
    flash(f"تم توليد {count} كود بنجاح للشهر {code_month}!", "success")
    return redirect(url_for('admin_dashboard'))

# ... بقية المسارات الخاصة بتسجيل الدخول وفضاء التلميذ ...
