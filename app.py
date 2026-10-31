from datetime import datetime
import random
import string
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "dekiche_academy_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# جدول التلاميذ والأكواد الشهرية
class StudentCode(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  code = db.Column(db.String(50), unique=True, nullable=False)
  student_name = db.Column(db.String(100), nullable=True)
  expiry_date = db.Column(db.String(20), nullable=False)
  is_used = db.Column(db.Boolean, default=False)


# جدول الدروس المرئية
class VideoLesson(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(200), nullable=False)
  video_url = db.Column(db.String(300), nullable=False)
  order_num = db.Column(db.Integer, default=1)


with app.app_context():
  db.create_all()


# صفحة تسجيل الدخول / تفعيل الكود لأول مرة
@app.route("/", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    entered_code = request.form.get("code").strip().upper()
    student_name = request.form.get("student_name", "").strip()

    code_obj = StudentCode.query.filter_by(code=entered_code).first()

    if not code_obj:
      flash("الكود غير صحيح، تأكد من إدخاله بشكل سليم.", "danger")
      return render_template("login.html")

    today = datetime.now().strftime("%Y-%m-%d")
    if code_obj.expiry_date < today:
      flash("عذراً، انتهت صلاحية هذا الكود لهذا الشهر.", "danger")
      return render_template("login.html")

    if not code_obj.is_used:
      if not student_name:
        return render_template(
            "login.html", ask_name=True, entered_code=entered_code
        )
      else:
        code_obj.student_name = student_name
        code_obj.is_used = True
        db.session.commit()

    session["student_name"] = code_obj.student_name
    session["logged_in"] = True
    return redirect(url_for("dashboard"))

  return render_template("login.html")


# صفحة عرض الدروس للتلميذ
@app.route("/dashboard")
def dashboard():
  if not session.get("logged_in"):
    return redirect(url_for("login"))

  lessons = VideoLesson.query.order_by(VideoLesson.order_num.asc()).all()
  return render_template(
      "dashboard.html",
      student_name=session.get("student_name"),
      lessons=lessons,
  )


# لوحة تحكم الأستاذ (الإدارة الشاملة)
@app.route("/admin", methods=["GET", "POST"])
def admin():
  action = request.form.get("action")

  if action == "generate_codes":
    expiry = request.form.get("expiry_date")
    count = int(request.form.get("count", 10))
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    for _ in range(count):
      random_code = "".join(random.choices(chars, k=6))
      while StudentCode.query.filter_by(code=random_code).first():
        random_code = "".join(random.choices(chars, k=6))
      db.session.add(StudentCode(code=random_code, expiry_date=expiry))

    db.session.commit()
    flash(f"تم توليد {count} كوداً جديداً بنجاح!", "success")

  elif action == "add_lesson":
    title = request.form.get("title")
    video_url = request.form.get("video_url")
    order_num = int(request.form.get("order_num", 1))

    if "watch?v=" in video_url:
      video_url = video_url.replace("watch?v=", "embed/")
    elif "youtu.be/" in video_url:
      video_url = video_url.replace("youtu.be/", "www.youtube.com/embed/")

    db.session.add(
        VideoLesson(title=title, video_url=video_url, order_num=order_num)
    )
    db.session.commit()
    flash("تم إضافة الدرس وترتيبه بنجاح!", "success")

    return redirect(url_for("admin"))

  codes = StudentCode.query.all()
  lessons = VideoLesson.query.order_by(VideoLesson.order_num.asc()).all()
  return render_template("admin.html", codes=codes, lessons=lessons)


@app.route("/admin/delete_code/<int:id>")
def delete_code(id):
  db.session.delete(StudentCode.query.get_or_404(id))
  db.session.commit()
  flash("تم حذف الكود.", "success")
  return redirect(url_for("admin"))


@app.route("/admin/delete_lesson/<int:id>")
def delete_lesson(id):
  db.session.delete(VideoLesson.query.get_or_404(id))
  db.session.commit()
  flash("تم حذف الدرس.", "success")
  return redirect(url_for("admin"))


@app.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("login"))


if __name__ == "__main__":
  app.run(debug=True)