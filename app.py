from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import random
import string
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'hamza_secret_key_academy'

def get_db_connection():
    conn = psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    return conn

# دالة توليد أكواد عشوائية
def generate_random_codes(count=10, prefix="HAMZA"):
    codes = []
    for _ in range(count):
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        codes.append(f"{prefix}-{suffix}")
    return codes

# الصفحة الرئيسية (توجيه لصفحة دخول الأستاذ أو يمكن تخصيصها)
@app.route('/')
def home():
    return redirect(url_for('admin_login'))

# مسار تسجيل دخول الأستاذ
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'hamza123':  # يمكنك تغيير كلمة المرور هنا
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('كلمة المرور غير صحيحة!', 'danger')
    return render_template('admin_login.html')

# لوحة تحكم الأستاذ
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # جلب جميع الدروس مرتبة حسب السنة والمادة والشهر والترتيب
    cur.execute("SELECT * FROM lessons ORDER BY grade, subject, lesson_month, order_index")
    lessons = cur.fetchall()
    
    # جلب التلاميذ المسجلين
    cur.execute("SELECT * FROM access_codes WHERE student_name IS NOT NULL ORDER BY created_at DESC")
    students = cur.fetchall()
    
    # جلب آخر الأكواد المولدة لتمكين طباعتها ونسخها
    cur.execute("SELECT code FROM access_codes WHERE is_used = FALSE ORDER BY id DESC LIMIT 50")
    recent_codes = [row['code'] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return render_template('admin.html', lessons=lessons, students=students, recent_codes=recent_codes)

# إضافة درس جديد مع السنة والمادة
@app.route('/admin/add_lesson', methods=['POST'])
def add_lesson():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    title = request.form['title']
    youtube_url = request.form['youtube_url']
    grade = request.form['grade']       # السنة الدراسية
    subject = request.form['subject']   # المادة
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
    
    flash("تمت إضافة الدرس بنجاح!", "success")
    return redirect(url_for('admin_dashboard'))

# توليد دفعة أكواد عشوائية
@app.route('/admin/generate_batch_codes', methods=['POST'])
def generate_batch_codes():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
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

# فضاء التلميذ (عرض الدروس حسب شهر الكود الخاص به)
@app.route('/student')
def student_space():
    if not session.get('student_logged_in'):
        return redirect(url_for('home')) # أو مسار تسجيل دخول التلميذ
        
    student_month = session.get('student_month', 1)
    student_name = session.get('student_name', 'تلميذ')
    
    conn = get_db_connection()
    cur = conn.cursor()
    # جلب الدروس المطابقة لشهر التلميذ فقط
    cur.execute("SELECT * FROM lessons WHERE lesson_month = %s ORDER BY grade, subject, order_index", (student_month,))
    lessons = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('student.html', lessons=lessons, student_name=student_name)

# تسجيل الخروج العام
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)
