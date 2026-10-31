from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
import os

app = Flask(__name__)
app.secret_key = 'dekiche_secret_key_2026'

# إعداد قاعدة البيانات الدائمة SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///academy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# إبقاء جلسة الدخول نشطة لمدة 30 يوماً
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=30)

# جدول الدروس
class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    grade = db.Column(db.String(50), nullable=False)      # السنة الدراسية للدرس
    subject = db.Column(db.String(50), nullable=False)    # المادة للدرس
    video_url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)

# جدول الأكواد المخصصة لكل تلميذ
class StudentCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    student_name = db.Column(db.String(100), nullable=True)
    grade = db.Column(db.String(50), nullable=False)      # السنة المخصصة للتلميذ
    subject = db.Column(db.String(50), nullable=False)    # المادة المخصصة للتلميذ

with app.app_context():
    db.create_all()

# الصفحة الرئيسية (عرض الدروس حسب صلاحية التلميذ أو الأستاذ)
@app.route('/')
def index():
    if session.get('admin_logged_in'):
        lessons = Lesson.query.order_by(Lesson.id.desc()).all()
        return render_template('index.html', lessons=lessons, role='admin')
    
    if session.get('student_logged_in'):
        s_grade = session.get('student_grade')
        s_subject = session.get('student_subject')
        lessons = Lesson.query.filter_by(grade=s_grade, subject=s_subject).order_by(Lesson.id.desc()).all()
        return render_template('index.html', lessons=lessons, role='student')
    
    return render_template('student_login.html')

# معالجة تسجيل دخول التلميذ بالكود
@app.route('/student_login', methods=['POST'])
def student_login():
    code_text = request.form.get('code')
    student_obj = StudentCode.query.filter_by(code=code_text).first()
    
    if student_obj:
        session['student_logged_in'] = True
        session['student_code'] = student_obj.code
        session['student_name'] = student_obj.student_name
        session['student_grade'] = student_obj.grade
        session['student_subject'] = student_obj.subject
        flash('تم تسجيل دخولك بنجاح.', 'success')
        return redirect(url_for('index'))
    else:
        flash('الكود غير صحيح أو غير مفعل، يرجى التحقق.', 'danger')
        return redirect(url_for('index'))

# صفحة عرض درس مفرد
@app.route('/lesson/<int:lesson_id>')
def view_lesson(lesson_id):
    if not session.get('admin_logged_in') and not session.get('student_logged_in'):
        flash('يرجى تسجيل الدخول بكود التلميذ أولاً.', 'warning')
        return redirect(url_for('index'))
        
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if session.get('student_logged_in'):
        if lesson.grade != session.get('student_grade') or lesson.subject != session.get('student_subject'):
            flash('عذراً، هذا الدرس ليس ضمن تخصيص الكود الخاص بك.', 'danger')
            return redirect(url_for('index'))
            
    return render_template('lesson_detail.html', lesson=lesson)

# تسجيل دخول الأستاذ
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == '1234':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('كلمة المرور غير صحيحة!', 'danger')
    return render_template('admin_login.html')

# لوحة تحكم الأستاذ
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_lesson':
            title = request.form.get('title')
            grade = request.form.get('grade')
            subject = request.form.get('subject')
            video_url = request.form.get('video_url')
            description = request.form.get('description')
            
            new_lesson = Lesson(title=title, grade=grade, subject=subject, video_url=video_url, description=description)
            db.session.add(new_lesson)
            db.session.commit()
            flash('تم إضافة الدرس وتصنيفه بنجاح وحفظه للأبد!', 'success')
            
        elif action == 'add_code':
            code = request.form.get('code')
            student_name = request.form.get('student_name')
            grade = request.form.get('grade')
            subject = request.form.get('subject')
            
            if code:
                existing = StudentCode.query.filter_by(code=code).first()
                if not existing:
                    new_code = StudentCode(code=code, student_name=student_name, grade=grade, subject=subject)
                    db.session.add(new_code)
                    db.session.commit()
                    flash('تم حفظ كود التلميذ مع تخصيص سنته ومادته بنجاح!', 'success')
                else:
                    flash('هذا الكود موجود مسبقاً!', 'warning')
                    
        return redirect(url_for('admin_dashboard'))
        
    lessons = Lesson.query.order_by(Lesson.id.desc()).all()
    codes = StudentCode.query.all()
    return render_template('admin_dashboard.html', lessons=lessons, codes=codes)

# حذف درس
@app.route('/admin/delete_lesson/<int:lesson_id>')
def delete_lesson(lesson_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    lesson = Lesson.query.get_or_404(lesson_id)
    db.session.delete(lesson)
    db.session.commit()
    flash('تم حذف الدرس بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

# حذف كود تلميذ
@app.route('/admin/delete_code/<int:code_id>')
def delete_code(code_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    code_item = StudentCode.query.get_or_404(code_id)
    db.session.delete(code_item)
    db.session.commit()
    flash('تم حذف الكود بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return "عذراً، الصفحة غير موجودة. <a href='/'>العودة للرئيسية</a>", 404

if __name__ == '__main__':
    app.run(debug=True)