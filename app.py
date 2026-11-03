from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dar_daqiche_secret_key_2026")

# قراءة وتنظيف متغيرات البيئة بسلامة تامة
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

# حماية التطبيق من الانهيار إذا كانت المتغيرات فارغة مؤقتاً أثناء الإقلاع
if not SUPABASE_URL or not SUPABASE_URL.startswith("http"):
    print("⚠️ تحذير: SUPABASE_URL غير مضبوط بشكل صحيح في البيئة، يتم استخدام رابط مؤقت لتفادي التوقف.")
    SUPABASE_URL = "https://placeholder.supabase.co"
    SUPABASE_KEY = "placeholder_key"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# كلمات المرور
ADMIN_PASSWORD = "admin_secure_2026"
TEACHER_PASSWORD = "teacher_password_2026"

@app.route('/')
def home():
    return render_template('index.html')

# --- بوابة التلميذ (إدخال الكود أو الدخول بالاسم والهاتف) ---
@app.route('/student-login', methods=['POST'])
def student_login():
    action = request.form.get('action')
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')

    if action == 'login':
        # التحقق من وجود التلميذ في جدول الأكواد المستعملة
        res = supabase.table('access_codes').select('*').eq('phone', phone).eq('student_name', full_name).execute()
        if res.data:
            session['student_name'] = full_name
            session['phone'] = phone
            return redirect(url_for('student_dashboard'))
        else:
            flash("البيانات غير صحيحة أو لم تقم بتفعيل كود من قبل.", "danger")
            return redirect(url_for('home'))

    elif action == 'redeem':
        code_text = request.form.get('code')
        # البحث عن الكود في قاعدة البيانات والتأكد أنه غير مستعمل
        code_res = supabase.table('access_codes').select('*').eq('code', code_text).eq('is_used', False).execute()
        
        if not code_res.data:
            flash("الكود غير صالح أو تم استخدامه مسبقاً!", "danger")
            return redirect(url_for('home'))
        
        code_data = code_res.data[0]

        # تحديث الكود ليرتبط بالتلميذ ويصبح مستخدماً
        supabase.table('access_codes').update({
            'student_name': full_name,
            'phone': phone,
            'is_used': True
        }).eq('id', code_data['id']).execute()

        session['student_name'] = full_name
        session['phone'] = phone
        flash("تم تفعيل اشتراكك بنجاح!", "
