import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'dekiche_academy_secret_key_2026'

# إنشاء قاعدة البيانات والجداول تلقائياً
def init_db():
    conn = sqlite3.connect('academy.db')
    cursor = conn.cursor()
    
    # جدول الدروس
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # جدول الأكواد والمستخدمين
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
    
    # كود تجريبي ينشأ تلقائياً عند التشغيل الأول
    cursor.execute('''
        INSERT OR IGNORE INTO access_codes (code, student_name, grade, subject, expires_at)
        VALUES (?, ?, ?, ?, ?)
    ''', ('12345', 'حمزة عباد', 'السنة الخامسة ابتدائي', 'اللغة العربية', '2026-12-31 23:59:59'))
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('academy.db')
    conn.row_factory = sqlite3.Row
    return conn

# الصفحة الرئيسية للتلميذ (عرض دروسه المخصصة)
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
        code = request.form.get('code', '').strip()
        
        # دخول المشرف العام
        if code == 'admin123':
            session['role'] = 'admin'
            session['student_name'] = 'المشرف العام'
            return redirect(url_for('dashboard'))
            
        # التحقق من كود التلميذ
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

# صفحة عرض تفاصيل الدرس الواحد
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

# لوحة تحكم المشرف
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
            
        # إضافة كود تلميذ جديد
        elif action == 'add_code':
            code = request.form.get('code')
            student_name = request.form.get('student_name')
            grade = request.form.get('grade')
            subject = request.form.get('subject')
            expires_at = request.form.get('expires_at')
            
            try:
                conn.execute(
                    'INSERT INTO access_codes (code, student_name, grade, subject, expires_at) VALUES (?, ?, ?, ?, ?)',
                    (code, student_name, grade, subject, expires_at)
                )
                conn.commit()
                flash('تم إنشاء كود التلميذ بنجاح!')
            except sqlite3.IntegrityError:
                flash('هذا الكود موجود مسبقاً، يرجى اختيار رمز آخر.')
                
        return redirect(url_for('dashboard'))
        
    lessons = conn.execute('SELECT * FROM lessons').fetchall()
    codes = conn.execute('SELECT * FROM access_codes').fetchall()
    conn.close()
    
    return render_template('dashboard.html', lessons=lessons, codes=codes)

# صفحة الملف الشخصي
@app.route('/profile')
def profile():
    if 'role' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html')

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)