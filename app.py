from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'dekiche_academy_secret_key'

# دالة الاتصال بقاعدة البيانات
def get_db_connection():
    conn = sqlite3.connect('academy.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    role = session.get('role', 'student')
    conn = get_db_connection()
    
    # إذا كان الطالب مسجلاً الدخول، نعرض له دروس سنته ومادته فقط
    if role == 'student':
        grade = session.get('student_grade', '')
        subject = session.get('student_subject', '')
        lessons = conn.execute('SELECT * FROM lessons WHERE grade = ? AND subject = ?', (grade, subject)).fetchall()
    else:
        # المشرف يرى كل الدروس
        lessons = conn.execute('SELECT * FROM lessons').fetchall()
        
    conn.close()
    return render_template('index.html', lessons=lessons, role=role)

@app.route('/lesson/<int:lesson_id>')
def lesson_detail(lesson_id):
    conn = get_db_connection()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    conn.close()
    if not lesson:
        flash('الدرس غير موجود')
        return redirect(url_for('index'))
    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)