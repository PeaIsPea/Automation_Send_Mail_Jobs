import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime

# --- KHỞI TẠO ỨNG DỤNG VÀ CÁC EXTENSION ---
app = Flask(__name__)

# Cấu hình cơ bản
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Khởi tạo các đối tượng
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- ĐỊNH NGHĨA MODELS (BẢNG DATABASE) ---

# Model cho Admin
class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

# Model cho Job
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False, default='Ho Chi Minh City')
    job_type = db.Column(db.String(50), nullable=False, default='Full-time')
    team = db.Column(db.String(50), nullable=False, default='Engineering')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    posted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deadline_at = db.Column(db.DateTime, nullable=True)
    applications = db.relationship('Application', backref='job', lazy=True, cascade="all, delete-orphan")

# Model cho Application
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    cv_path = db.Column(db.String(255), nullable=False)
    cover_letter = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)

    def __repr__(self):
        job_title = self.job.title if self.job else "N/A"
        return f"Application('{self.first_name}', '{self.last_name}', '{job_title}')"

# --- CẤU HÌNH FLASK-LOGIN ---
@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# --- ROUTE ĐĂNG NHẬP / ĐĂNG XUẤT ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin)
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất.', 'success')
    return redirect(url_for('home'))

# --- ROUTE DÀNH CHO ADMIN (CRUD JOBS) ---
@app.route('/admin/dashboard')
@login_required
def dashboard():
    jobs = Job.query.order_by(Job.posted_at.desc()).all()
    return render_template('admin/dashboard.html', jobs=jobs)

@app.route('/admin/job/add', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        job_type = request.form.get('job_type')
        team = request.form.get('team')
        deadline_str = request.form.get('deadline_at')
        deadline_at = datetime.strptime(deadline_str, '%Y-%m-%d') if deadline_str else None
        new_job = Job(title=title, description=description, location=location, 
                      job_type=job_type, team=team, deadline_at=deadline_at)
        db.session.add(new_job)
        db.session.commit()
        flash('Đã thêm công việc mới thành công!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('admin/job_form.html', title="Thêm công việc mới")

@app.route('/admin/job/edit/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    if request.method == 'POST':
        job.title = request.form.get('title')
        job.description = request.form.get('description')
        job.location = request.form.get('location')
        job.job_type = request.form.get('job_type')
        job.team = request.form.get('team')
        deadline_str = request.form.get('deadline_at')
        job.deadline_at = datetime.strptime(deadline_str, '%Y-%m-%d') if deadline_str else None
        job.is_active = 'is_active' in request.form
        db.session.commit()
        flash('Đã cập nhật công việc thành công!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('admin/job_form.html', title="Chỉnh sửa công việc", job=job)

@app.route('/admin/job/delete/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash('Đã xóa công việc thành công!', 'success')
    return redirect(url_for('dashboard'))

# --- PUBLIC ROUTES (DÀNH CHO ỨNG VIÊN) ---
@app.route('/')
def home():
    return render_template('public/home.html')

@app.route('/careers')
def careers():
    active_jobs = Job.query.filter_by(is_active=True).order_by(Job.posted_at.desc()).all()
    return render_template('public/careers.html', jobs=active_jobs)

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template('public/job_detail.html', job=job)

# Route để xử lý việc nộp hồ sơ
@app.route('/apply/<int:job_id>', methods=['POST'])
def apply(job_id):
    job = Job.query.get_or_404(job_id)
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        cover_letter = request.form.get('cover_letter')
        cv_file = request.files.get('cv')

        if not cv_file or cv_file.filename == '':
            flash('Vui lòng tải lên file CV của bạn.', 'danger')
            return redirect(url_for('job_detail', job_id=job.id))

        upload_folder = 'uploads'
        os.makedirs(upload_folder, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{cv_file.filename}"
        cv_path = os.path.join(upload_folder, filename)
        cv_file.save(cv_path)

        new_application = Application(
            first_name=first_name, last_name=last_name, email=email, phone=phone,
            cover_letter=cover_letter, cv_path=cv_path, job_id=job.id
        )
        db.session.add(new_application)
        db.session.commit()

        # === PHẦN GIAO TIẾP VỚI N8N ĐÃ ĐƯỢC THÊM VÀO ĐÂY ===
        try:
            absolute_cv_path = os.path.abspath(cv_path)
            
            payload = {
                'job_title': job.title,
                'job_description': job.description,
                'cv_path': absolute_cv_path,
                'candidate_email': email,
                'candidate_name': f"{first_name} {last_name}",
                'application_id': new_application.id
            }

            # QUAN TRỌNG: Dán URL Webhook (Test hoặc Production) của bạn vào đây
            #webhook_url = "http://localhost:5678/webhook-test/2a11c345-1c6c-47f3-9983-e32ac4609bf4" #This is Test
            webhook_url = "http://localhost:5678/webhook/2a11c345-1c6c-47f3-9983-e32ac4609bf4" # This is Production
            
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code == 200:
                print(f"Signal cho Application ID {new_application.id} đã gửi thành công đến n8n.")
            else:
                print(f"Lỗi khi gửi signal đến n8n: Status {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Đã xảy ra lỗi nghiêm trọng khi gửi request đến n8n: {e}")
            
        flash('Nộp hồ sơ thành công! Chúng tôi sẽ liên hệ với bạn sớm.', 'success')
        return redirect(url_for('job_detail', job_id=job.id))
    
# --- CHẠY ỨNG DỤNG ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

