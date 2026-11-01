import sqlite3
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'dekiche_academy_secret_key_2026'

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
            expires_at TEXT NOT NULL,
            phone TEXT,
            is_registered INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('academy.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_unique_code():
    conn = get_db_connection()
    while True:
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(chars, k=6))
        existing = conn.execute('SELECT id FROM access_codes WHERE code = ?', (code,)).fetchone()
        if not existing:
            conn.close()
            return code

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
            'SELECT * FROM lessons WHERE grade = ? AND subject = ? ORDER BY id DESC', 
            (grade, subject)
        ).fetchall()
    else:
        lessons = conn.execute('SELECT * FROM lessons ORDER BY grade, subject, id DESC').fetchall()
        
    conn.close()
    return render_template('index.html', lessons=lessons)

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
        
        if code_data:
            expires_at = datetime.strptime(code_data['expires_at'], '%Y-%m-%d %H:%M:%S')
            if datetime.now() > expires_at:
                conn.close()
                flash('عذراً، انتهت مدة صلاحية هذا الكود.')
            else:
                if code_data['is_registered'] == 0:
                    conn.close()
                    return render_template('complete_register.html', code=code)
                else:
                    session['role'] = 'student'
                    session['student_name'] = code_data['student_name']
                    session['student_grade'] = code_data['grade']
                    session['student_subject'] = code_data['subject']
                    conn.close()
                    return redirect(url_for('index'))
        else:
            conn.close()
            flash('رمز الدخول غير صحيح، يرجى التأكد وإعادة المحاولة.')
            
    return render_template('student_login.html')

@app.route('/complete_register', methods=['POST'])
def complete_register():
    code = request.form.get('code')
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    
    if not full_name or not phone:
        flash('يرجى إدخال الاسم واللقب ورقم الهاتف.')
        return render_template('complete_register.html', code=code)
        
    conn = get_db_connection()
    conn.execute(
        'UPDATE access_codes SET student_name = ?, phone = ?, is_registered = 1 WHERE code = ?',
        (full_name, phone, code)
    )
    conn.commit()
    
    code_data = conn.execute('SELECT * FROM access_codes WHERE code = ?', (code,)).fetchone()
    conn.close()
    
    session['role'] = 'student'
    session['student_name'] = code_data['student_name']
    session['student_grade'] = code_data['grade']
    session['student_subject'] = code_data['subject']
    
    return redirect(url_for('index'))

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

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if session.get('role') != 'admin':
        flash('عذراً، هذه الصفحة خاصة بالمشرف فقط.')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
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
            flash('تم إضافة الدرس وحفظه بنجاح!')
            
        elif action == 'delete_lesson':
            lesson_id = request.form.get('lesson_id')
            conn.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
            conn.commit()
            flash('تم حذف الدرس بنجاح.')
            
        elif action == 'generate_code':
            grade = request.form.get('grade')
            subject = request.form.get('subject')
            duration_days = int(request.form.get('duration_days', 30))
            count = int(request.form.get('count', 1))
            
            generated_count = 0
            for i in range(count):
                code = generate_unique_code()
                expires_at = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d %H:%M:%S')
                
                try:
                    conn.execute(
                        'INSERT INTO access_codes (code, student_name, grade, subject, expires_at, is_registered) VALUES (?, ?, ?, ?, ?, 0)',
                        (code, f"تلميذ جديد {i+1}", grade, subject, expires_at)
                    )
                    generated_count += 1
                except sqlite3.IntegrityError:
                    continue
                    
            conn.commit()
            flash(f'تم توليد {generated_count} كود بنجاح للطور ({grade} - {subject})!')
            
        return redirect(url_for('dashboard'))
        
    lessons = conn.execute('SELECT * FROM lessons ORDER BY grade, subject, id DESC').fetchall()
    codes = conn.execute('SELECT * FROM access_codes ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('dashboard.html', lessons=lessons, codes=codes)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
