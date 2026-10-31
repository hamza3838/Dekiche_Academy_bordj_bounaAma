import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'dekiche_academy_secret_key'

# دالة لإنشاء قاعدة البيانات والجداول تلقائياً لمنع ظهور خطأ 500
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
