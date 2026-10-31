import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'dekiche_academy_secret_key'

# دالة لإنشاء قاعدة البيانات والجداول تلقائياً لمنع ظهور أي خطأ
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
    conn.commit()
    conn.close()

# تشغيل إنشاء قاعدة البيانات عند بدء تشغيل التطبيق
init_db()

def get_db_connection():
    conn = sqlite3.connect('academy.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    # التحقق مما إذا كان المستخدم مسجلاً للدخول أم لا
    if 'role' not in session:
        return redirect(url_for('login'))
        
    role = session.get('role', 'student')
    conn = get_db_connection()
    
    if role == 'student':
        grade = session.get('student_grade', '')
        subject = session.get('student_subject', '')
        lessons = conn.execute('SELECT * FROM lessons WHERE grade = ? AND subject = ?', (grade, subject)).fetchall()
    else:
        lessons = conn.execute('SELECT * FROM lessons').fetchall()
        
    conn.close()
    return render_template('index.html', lessons=lessons, role=role)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        code = request.form.get('code')
        
        # كلمة سر المشرف (يمكنك تغييرها لاحقاً)
        if code == 'admin123':
            session['role'] = 'admin'
            return redirect(url_for('index'))
        elif code and len(code.strip()) > 0:
            # دخول التلامذة بناء على الكود
            session['role'] = 'student'
            session['student_grade'] = 'السنة الخامسة ابتدائي'
            session['student_subject'] = 'اللغة العربية'
            return redirect(url_for('index'))
        else:
            flash('الرجاء إدخال رمز صحيح')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
