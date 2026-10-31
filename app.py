import sqlite3
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'dekiche_academy_secret_key_2026'

# إنشاء قاعدة البيانات والجداول تلقائياً
def init_db():
    conn = sqlite3.connect('academy.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            student_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('academy.db')
    conn.row_factory = sqlite3.Row
    return conn

# دالة توليد الأكواد (أرقام وحروف إنجليزية كبيرة فقط - بدون رموز)
def generate_unique_code():
    conn = get_db_connection()
    while True:
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(chars, k=6))
        
        existing = conn.execute('SELECT id FROM access_codes WHERE code = ?', (code,)).fetchone()
        if not existing:
            conn.close()
            return code

# الصفحة الرئيسية للتلميذ
@app.route('/')
def index():
    if 'role' not in session:
        return redirect(url_for('login'))
        
    role = session.get('role', 'student')
    conn = get_db_connection()
    
    if role == 'student':
        grade = session.get('student_grade', '')
        subject = session.get('student_subject', '')
        lessons = conn.execute(
            'SELECT * FROM lessons WHERE grade = ? AND subject = ?', 
            (grade, subject)
        ).fetchall()
    else:
        lessons = conn.execute('SELECT * FROM lessons').fetchall()
        
    conn.close()
    return render_template('index.html', lessons=lessons)

# صفحة تسجيل دخول التلامذة
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        
        if code == 'ADMIN123':
            session['role'] = 'admin'
            session['student_name'] = 'المشرف العام'
            return redirect(url_for('dashboard'))
            
        conn = get_db_connection()
        code_data = conn.execute(
            'SELECT * FROM access_codes WHERE code = ?', (code,)
        ).fetchone()
        conn.close()
        
        if code_data:
            expires_at = datetime.strptime(code_data['expires_at'], '%Y-%m-%d %H:%M:%S')
            if datetime.now() > expires_at:
                flash('عذراً، انتهت مدة صلاحية هذا الكود.')
            else:
                session['role'] = 'student'
                session['student_name'] = code_data['student_name']
                session['student_grade'] = code_data['grade']
                session['student_subject'] = code_data['subject']
                return redirect(url_for('index'))
        else:
            flash('رمز الدخول غير صحيح، يرجى التأكد وإعادة المحاولة.')
            
    return render_template('student_login.html')

# صفحة تفاصيل الدرس
@app.route('/lesson/<int:lesson_id>')
def lesson_detail(lesson_id):
    if 'role' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    conn.close()
    
    if not lesson:
        flash('عذراً، هذا الدرس غير موجود.')
        return redirect(url_for('index'))
        
    return render_template('lesson.html', lesson=lesson)

# لوحة تحكم المشرف (تدعم توليد دفعة أكواد)
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if session.get('role') != 'admin':
        flash('عذراً، هذه الصفحة خاصة بالمشرف فقط.')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # إضافة درس جديد
        if action == 'add_lesson':
            title = request.form.get('title')
            grade = request.form.get('grade')
            subject = request.form.get('subject')
            description = request.form.get('description')
            
            conn.execute(
                'INSERT INTO lessons (title, grade, subject, description) VALUES (?, ?, ?, ?)',
                (title, grade, subject, description)
            )
            conn.commit()
            flash('تم إضافة الدرس بنجاح!')
            
        # توليد دفعة أكواد تلامذة تلقائياً
        elif action == 'generate_code':
            student_prefix = request.form.get('student_prefix', 'تلميذ')
            grade = request.form.get('grade')
            subject = request.form.get('subject')
            duration_days = int(request.form.get('duration_days', 30))
            count = int(request.form.get('count', 1))
            
            generated_count = 0
            for i in range(count):
                code = generate_unique_code()
                expires_at = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d %H:%M:%S')
                student_name = f"{student_prefix} {i+1}"
                
                try:
                    conn.execute(
                        'INSERT INTO access_codes (code, student_name, grade, subject, expires_at) VALUES (?, ?, ?, ?, ?)',
                        (code, student_name, grade, subject, expires_at)
                    )
                    generated_count += 1
                except sqlite3.IntegrityError:
                    continue
                    
            conn.commit()
            flash(f'تم توليد دفعة جديدة بنجاح: {generated_count} كود للطور ({grade} - {subject})!')
            
        return redirect(url_for('dashboard'))
        
    lessons = conn.execute('SELECT * FROM lessons').fetchall()
    codes = conn.execute('SELECT * FROM access_codes ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('dashboard.html', lessons=lessons, codes=codes)

@app.route('/profile')
def profile():
    if 'role' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
