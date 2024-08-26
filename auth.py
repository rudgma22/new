import os
import random
import smtplib
from email.mime.text import MIMEText
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory
from models import db, add_student, add_teacher, add_admin, Student, Teacher, Admin, OutingRequest, Extern

import bcrypt
from dotenv import load_dotenv
import logging
from datetime import datetime, time

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

auth_bp = Blueprint('auth', __name__)

def send_verification_email(email, code):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    subject = "김천고등학교 외출 관리 시스템 - 이메일 인증 코드"
    body = f"인증 코드는 {code} 입니다. 이 코드를 입력해 인증을 완료해주세요."

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = email

    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email, msg.as_string())
        server.quit()
        print("이메일이 성공적으로 전송되었습니다.")
    except Exception as e:
        print(f"이메일 전송 중 오류 발생: {e}")

@auth_bp.route('/')
def index():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    user = None
    if role == 'student':
        user = Student.query.filter_by(username=username).first()
    elif role == 'teacher':
        user = Teacher.query.filter_by(username=username).first()

    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        session['user_id'] = user.id
        session['role'] = role
        if role == 'student':
            return redirect(url_for('views.student_home'))
        elif role == 'teacher':
            return redirect(url_for('views.teacher_home'))

    else:
        flash('Invalid credentials', 'danger')
        return redirect(url_for('auth.index'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        email = request.form.get('email').strip() if role != 'admin' else None

        if role != 'admin' and not email:
            flash('이메일은 필수 입력 항목입니다.', 'danger')
            return redirect(url_for('auth.register'))

        if role != 'admin':
            existing_email = Student.query.filter_by(email=email).first() or Teacher.query.filter_by(email=email).first()
            if existing_email:
                flash('이미 사용 중인 이메일입니다. 다른 이메일을 사용하세요.', 'danger')
                return redirect(url_for('auth.register'))

        existing_user = Student.query.filter_by(username=username).first() or Teacher.query.filter_by(username=username).first() or Admin.query.filter_by(username=username).first()
        if existing_user:
            flash('이미 사용 중인 아이디입니다. 다른 아이디를 사용하세요.', 'danger')
            return redirect(url_for('auth.register'))

        if role == 'student':
            name = request.form['student_name']
            grade = request.form['grade']
            student_class = request.form['student_class']
            number = request.form['number']
            barcode = request.form['barcode']

            existing_student = Student.query.filter_by(barcode=barcode).first()
            if existing_student:
                flash('이미 사용 중인 바코드입니다. 다른 바코드를 사용하세요.', 'danger')
                return redirect(url_for('auth.register'))

            add_student(name, grade, student_class, number, username, password, barcode, email)

        elif role == 'teacher':
            name = request.form['teacher_name']
            grade = request.form['grade']
            teacher_class = request.form['teacher_class']

            if not grade or not teacher_class:
                flash('학년과 반을 모두 선택해야 합니다.', 'danger')
                return redirect(url_for('auth.register'))

            try:
                add_teacher(name, grade, teacher_class, username, password, email)
            except Exception as e:
                logging.error(f"Error during teacher registration: {e}")
                flash('교사 회원가입 중 문제가 발생했습니다. 다시 시도하세요.', 'danger')
                return redirect(url_for('auth.register'))

        elif role == 'admin':
            name = request.form['admin_name']
            add_admin(name, username, password)

        flash('회원가입이 성공적으로 완료되었습니다!', 'success')
        return redirect(url_for('auth.index'))

    return render_template('register.html')

@auth_bp.route('/find_id')
def find_id():
    return render_template('find_id.html')

@auth_bp.route('/find_pw')
def find_pw():
    return render_template('find_pw.html')

@auth_bp.route('/student_find_id', methods=['GET', 'POST'])
def student_find_id():
    if request.method == 'POST':
        name = request.form.get('name')
        grade = request.form.get('grade')
        student_class = request.form.get('class')
        number = request.form.get('number')
        email = request.form.get('email')

        user = Student.query.filter_by(name=name, grade=grade, student_class=student_class, number=number, email=email).first()

        if user:
            verification_code = random.randint(100000, 999999)
            session['verification_code'] = verification_code
            session['user_id'] = user.id
            session['role'] = 'student'
            send_verification_email(email, verification_code)
            return redirect(url_for('auth.verify_code', action='find_id'))
        else:
            flash('해당 정보로 아이디를 찾을 수 없습니다.', 'danger')
            return render_template('find_id.html')

    return render_template('student_find_id.html')

@auth_bp.route('/teacher_find_id', methods=['GET', 'POST'])
def teacher_find_id():
    if request.method == 'POST':
        name = request.form.get('name')
        grade = request.form.get('grade')
        teacher_class = request.form.get('class')
        email = request.form.get('email')

        user = Teacher.query.filter_by(name=name, grade=grade, teacher_class=teacher_class, email=email).first()

        if user:
            verification_code = random.randint(100000, 999999)
            session['verification_code'] = verification_code
            session['user_id'] = user.id
            session['role'] = 'teacher'
            send_verification_email(email, verification_code)
            return redirect(url_for('auth.verify_code', action='find_id'))
        else:
            flash('해당 정보로 아이디를 찾을 수 없습니다.', 'danger')
            return render_template('teacher_find_id.html')

    return render_template('teacher_find_id.html')

@auth_bp.route('/student_change_pw', methods=['GET', 'POST'])
def student_change_pw():
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        grade = request.form.get('grade')
        student_class = request.form.get('class')
        number = request.form.get('number')
        email = request.form.get('email')

        user = Student.query.filter_by(username=username, name=name, grade=grade, student_class=student_class, number=number, email=email).first()

        if user:
            verification_code = random.randint(100000, 999999)
            session['verification_code'] = verification_code
            session['user_id'] = user.id
            session['role'] = 'student'
            send_verification_email(email, verification_code)
            # action 값을 'reset_password'로 설정하여 verify_code로 리디렉션
            return redirect(url_for('auth.verify_code', action='reset_password'))
        else:
            flash('해당 정보로 계정을 찾을 수 없습니다.', 'danger')
            return render_template('student_change_pw.html')

    return render_template('student_change_pw.html')


@auth_bp.route('/teacher_change_pw', methods=['GET', 'POST'])
def teacher_change_pw():
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        grade = request.form.get('grade')
        teacher_class = request.form.get('class')
        email = request.form.get('email')

        user = Teacher.query.filter_by(username=username, name=name, grade=grade, teacher_class=teacher_class, email=email).first()

        if user:
            verification_code = random.randint(100000, 999999)
            session['verification_code'] = verification_code
            session['user_id'] = user.id
            session['role'] = 'teacher'
            send_verification_email(email, verification_code)
            # action 값을 'reset_password'로 설정하여 verify_code로 리디렉션
            return redirect(url_for('auth.verify_code', action='reset_password'))
        else:
            flash('해당 정보로 계정을 찾을 수 없습니다.', 'danger')
            return render_template('teacher_change_pw.html')

    return render_template('teacher_change_pw.html')


@auth_bp.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    action = request.args.get('action')  # action 값을 여기서 미리 가져옵니다.

    if request.method == 'POST':
        input_code = request.form.get('verification_code')  # 사용자가 입력한 인증 코드를 가져옴
        if input_code and int(input_code) == session.get('verification_code'):
            user_role = session.get('role')  # 사용자의 역할을 가져옵니다.
            if action == 'find_id':
                user = Student.query.get(session['user_id']) if user_role == 'student' else Teacher.query.get(session['user_id'])
                if user_role == 'student':
                    return render_template('student_find_id_result.html', name=user.name, username=user.username)
                else:  # 'teacher'인 경우
                    return render_template('teacher_find_id_result.html', name=user.name, username=user.username)
            elif action == 'reset_password':
                # 비밀번호 재설정으로 리디렉션
                if user_role == 'student':
                    return redirect(url_for('auth.student_reset_password_form'))
                else:
                    return redirect(url_for('auth.teacher_reset_password_form'))
        else:
            flash('인증 코드가 올바르지 않습니다.', 'danger')
            return redirect(url_for('auth.verify_code', action=action))  # action을 다시 전달합니다.
    else:
        return render_template('verify_code.html', action=action)


@auth_bp.route('/student_reset_password_form', methods=['GET', 'POST'])
def student_reset_password_form():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.', 'danger')
            return redirect(url_for('auth.student_reset_password_form'))

        user = Student.query.get(session['user_id'])

        if user:
            user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.session.commit()
            return redirect(url_for('auth.student_reset_password_result'))
        else:
            flash('비밀번호 변경 중 오류가 발생했습니다.', 'danger')
            return redirect(url_for('auth.student_reset_password_form'))

    return render_template('student_change_pw_step2.html')

@auth_bp.route('/teacher_reset_password_form', methods=['GET', 'POST'])
def teacher_reset_password_form():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.', 'danger')
            return redirect(url_for('auth.teacher_reset_password_form'))

        user = Teacher.query.get(session['user_id'])

        if user:
            user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.session.commit()
            return redirect(url_for('auth.teacher_reset_password_result'))
        else:
            flash('비밀번호 변경 중 오류가 발생했습니다.', 'danger')
            return redirect(url_for('auth.teacher_reset_password_form'))

    return render_template('teacher_change_pw_step2.html')

@auth_bp.route('/student_reset_password_result')
def student_reset_password_result():
    return render_template('student_change_pw_result.html')

@auth_bp.route('/teacher_reset_password_result')
def teacher_reset_password_result():
    return render_template('teacher_change_pw_result.html')

from datetime import datetime, time
from models import db, add_student, add_teacher, add_admin, Student, Teacher, Admin, OutingRequest, Extern

@auth_bp.route('/barcode_scan', methods=['GET', 'POST'])
def barcode_scan():
    response_data = None  # 기본값 설정

    if request.method == 'POST':
        barcode = request.form.get('barcode')
        print(f"입력된 바코드: {barcode}")  # 디버깅을 위한 출력

        # extern 테이블에서 해당 바코드를 가진 학생이 있는지 확인
        extern_student = Extern.query.filter_by(barcode=barcode).first()
        current_time = datetime.now().time()
        print(f"현재 시간: {current_time}")  # 디버깅을 위한 출력

        # 통학생이고, 현재 시간이 9시부터 23시 사이라면 자동 승인
        if extern_student and time(18, 0) <= current_time <= time(23, 0):
            print(f"통학생 {extern_student.name}님이 통학 시간이므로 자동 승인됩니다.")  # 디버깅을 위한 출력
            response_data = {
                'barcode': extern_student.barcode,
                'student_name': extern_student.name,
                'outing_time': "통학생입니다.",  # 외출 시간 메시지 수정
                'status': '승인됨',
                'color': 'green',
                'sound': url_for('static', filename='Pling Sound.mp3'),
                'message': f"{extern_student.name}님은 통학이 승인되었습니다. 조심히 다녀오세요!"
            }
        else:
            # extern 테이블에 없는 학생이거나 통학생이지만 시간이 맞지 않는 경우 기존 로직 사용
            latest_outing_request = OutingRequest.query.filter_by(barcode=barcode).order_by(OutingRequest.start_time.desc()).first()

            if latest_outing_request:
                start_time = latest_outing_request.start_time
                end_time = latest_outing_request.end_time

                response_data = {
                    'barcode': latest_outing_request.barcode,
                    'student_name': latest_outing_request.student_name,
                    'outing_time': f"{start_time} ~ {end_time}",
                    'status': latest_outing_request.status,
                    'color': '',
                    'sound': '',
                    'message': ''
                }

                if latest_outing_request.status == '승인됨' and start_time <= datetime.now() <= end_time:
                    response_data['color'] = 'green'
                    response_data['sound'] = url_for('static', filename='Pling Sound.mp3')
                    response_data['message'] = f"{latest_outing_request.student_name}님은 외출이 가능합니다. 조심히 다녀오세요!"
                elif latest_outing_request.status == '대기중' and start_time <= datetime.now() <= end_time:
                    response_data['color'] = 'yellow'
                    response_data['sound'] = url_for('static', filename='Buzz 2.mp3')
                    response_data['message'] = "외출 신청이 대기중입니다. 승인 후 다시 인식해주세요."
                else:
                    response_data['color'] = 'red'
                    response_data['sound'] = url_for('static', filename='Buzz 2.mp3')
                    response_data['message'] = f"외출이 불가능합니다. 외출 가능한 시간은 {start_time} ~ {end_time}입니다."
            else:
                flash('해당 바코드로 외출 요청을 찾을 수 없습니다.', 'danger')
                print("해당 바코드로 외출 요청을 찾을 수 없습니다.")  # 디버깅을 위한 출력

    return render_template('barcode.html', response_data=response_data)
