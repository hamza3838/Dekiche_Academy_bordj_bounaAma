import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'dekiche_academy_secret_key_2026'

# رابط قاعدة البيانات السحابية من Supabase (ضع رابطك هنا أو كمتبي بيئي في Render)
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:YOUR_PASSWORD@db.xxxx.supabase.co:5432/postgres')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_codes (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            student_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            phone TEXT,
            is_registered INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def generate_unique_code():
    conn = get_db_connection()
    cursor = conn.cursor()
    while True:
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(chars, k=6))
        cursor.execute('SELECT id FROM access_codes WHERE code = %s', (code,))
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            return code

@app.route('/')
def index():
    if 'role' not in session:
        return redirect(url_for('login'))
        
    role = session.get('role', 'student')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if role == 'student':
        grade = session.get('student_grade', '')
        subject = session.get('student_subject', '')
        cursor.execute(
            'SELECT * FROM lessons WHERE grade = %s AND subject = %s ORDER BY id DESC', 
            (grade, subject)
        )
        lessons = cursor.fetchall()
    else:
        cursor.execute('SELECT * FROM lessons ORDER BY grade, subject, id DESC')
        lessons = cursor.fetchall()
        
    cursor.close()
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
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM access_codes WHERE code = %s', (code,))
        code_data = cursor.fetchone()
        
        if code_data:
            expires_at = datetime.strptime(code_data['expires_at'], '%Y-%m-%d %H:%M:%S')
            if datetime.now() > expires_at:
                cursor.close()
                conn.close()
                flash('عذراً، انتهت مدة صلاحية هذا الكود.')
            else:
                if code_data['is_registered'] == 0:
                    cursor.close()
                    conn.close()
                    return render_template('complete_register.html', code=code)
                else:
                    session['role'] = 'student'
                    session['student_name'] = code_data['student_name']
                    session['student_grade'] = code_data['grade']
                    session['student_subject'] = code_data['subject']
                    cursor.close()
                    conn.close()
                    return redirect(url_for('index'))
        else:
            cursor.close()
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
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE access_codes SET student_name = %s, phone = %s, is_registered = 1 WHERE code = %s',
        (full_name, phone, code)
    )
    conn.commit()
    
    cursor.execute('SELECT * FROM access_codes WHERE code = %s', (code,))
    code_data = cursor.fetchone()
    cursor.close()
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
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM lessons WHERE id = %s', (lesson_id,))
    lesson = cursor.fetchone()
    cursor.close()
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
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_lesson':
            title = request.form.get('title')
            grade = request.form.get('grade')
            subject = request.form.get('subject')
            description = request.form.get('description')
            
            cursor.execute(
                'INSERT INTO lessons (title, grade, subject, description) VALUES (%s, %s, %s, %s)',
                (title, grade, subject, description)
            )
            conn.commit()
            flash('تم إضافة الدرس وحفظه بنجاح!')
            
        elif action == 'delete_lesson':
            lesson_id = request.form.get('lesson_id')
            cursor.execute('DELETE FROM lessons WHERE id = %s', (lesson_id,))
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
                    cursor.execute(
                        'INSERT INTO access_codes (code, student_name, grade, subject, expires_at, is_registered) VALUES (%s, %s, %s, %s, %s, 0)',
                        (code, f"تلميذ جديد {i+1}", grade, subject, expires_at)
                    )
                    conn.commit()
                    generated_count += 1
                except Exception:
                    conn.rollback()
                    continue
                    
            flash(f'تم توليد {generated_count} كود بنجاح للطور ({grade} - {subject})!')
            
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
        
    cursor.execute('SELECT * FROM lessons ORDER BY grade, subject, id DESC')
    lessons = cursor.fetchall()
    cursor.execute('SELECT * FROM access_codes ORDER BY id DESC')
    codes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', lessons=lessons, codes=codes)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
