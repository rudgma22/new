from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from sqlalchemy.sql import text
from sqlalchemy import func
from models import get_db_connection, add_outing_request, approve_outing_request, OutingRequest, db, Student, Admin, get_outing_statistics
import bcrypt
from datetime import datetime

views_bp = Blueprint('views', __name__)

def row_to_dict(row):
    if row is None:
        return None
    return dict(row._mapping)


@views_bp.route('/student_home')
def student_home():
    if 'user_id' in session and session['role'] == 'student':
        conn = get_db_connection()
        # 학생 정보 가져오기
        student = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()
        student = row_to_dict(student)

        # 학생의 외출 신청 내역 가져오기
        outing_requests = conn.execute(text('SELECT * FROM outing_requests WHERE student_name = :name'),
                                       {'name': student['name']}).fetchall()
        outing_requests = [row_to_dict(request) for request in outing_requests]

        conn.close()

        # password_validated를 세션에서 가져오고, 기본값 False로 설정
        password_validated = session.get('password_validated', False)
        session['password_validated'] = False  # 항상 False로 초기화하여 매번 비밀번호를 확인하게 함

        return render_template('student_home.html',
                               student=student,
                               outing_requests=outing_requests,
                               password_validated=password_validated)  # 변수 전달
    else:
        return redirect(url_for('auth.index'))



@views_bp.route('/teacher_manage')
def teacher_manage():
    if 'user_id' in session and session['role'] == 'teacher':
        conn = get_db_connection()
        teacher = conn.execute(text('SELECT * FROM teachers WHERE id = :id'), {'id': session['user_id']}).fetchone()
        teacher = row_to_dict(teacher)
        requests = conn.execute(text(
            'SELECT * FROM outing_requests WHERE student_name IN (SELECT name FROM students WHERE grade = :grade AND student_class = :class)'),
            {'grade': teacher['grade'], 'class': teacher['teacher_class']}).fetchall()
        requests = [row_to_dict(request) for request in requests]
        conn.close()
        return render_template('student_manage.html', teacher=teacher, requests=requests)
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/admin_page')
def admin_page():
    if 'user_id' in session and session['role'] == 'admin':
        page = request.args.get('page', 1, type=int)
        grade = request.args.get('grade', 'all')
        student_class = request.args.get('student_class', 'all')

        students_query = Student.query

        if grade != 'all':
            students_query = students_query.filter_by(grade=grade)
        if student_class != 'all':
            students_query = students_query.filter_by(student_class=student_class)

        students = students_query.paginate(page=page, per_page=10)
        return render_template('admin_page.html', students=students, grade=grade, student_class=student_class)
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/apply_leave', methods=['POST'])
def apply_leave():
    if 'user_id' in session and session['role'] == 'student':
        student_id = session['user_id']
        start_time = datetime.fromisoformat(request.form['start_time'])
        end_time = datetime.fromisoformat(request.form['end_time'])
        reason = request.form['reason']
        if reason == '기타':
            other_reason = request.form['other_reason']
            reason = f'기타({other_reason})'

        conn = get_db_connection()
        student = conn.execute(text('SELECT name, barcode FROM students WHERE id = :id'), {'id': student_id}).fetchone()
        student = row_to_dict(student)

        # 최신 외출 신청을 조회하여 중복 방지
        existing_request = conn.execute(text(
            'SELECT end_time FROM outing_requests WHERE barcode = :barcode ORDER BY start_time DESC LIMIT 1'),
            {'barcode': student['barcode']}).fetchone()
        existing_request = row_to_dict(existing_request)

        if existing_request:
            existing_end_time = datetime.fromisoformat(existing_request['end_time'])
            if start_time <= existing_end_time:
                flash('이미 존재하는 외출 신청이 있습니다.', 'danger')
                conn.close()
                return redirect(url_for('views.student_home'))

        add_outing_request(student['name'], student['barcode'], start_time, end_time, reason)
        conn.close()
        flash('외출 신청이 성공적으로 완료되었습니다.', 'success')
        return redirect(url_for('views.student_home'))
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/approve_leave/<int:request_id>', methods=['POST'])
def approve_leave(request_id):
    if 'user_id' in session and session['role'] == 'teacher':
        approve_outing_request(request_id)
        return redirect(url_for('views.teacher_manage'))
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/reject_leave/<int:request_id>', methods=['POST'])
def reject_leave(request_id):
    if 'user_id' in session and session['role'] == 'teacher':
        rejection_reason = request.form.get('rejection_reason', '').strip()
        if not rejection_reason:
            flash('거절 사유를 입력해주세요')
            return redirect(url_for('views.teacher_manage'))

        outing_request = OutingRequest.query.get(request_id)
        if outing_request:
            outing_request.status = '거절됨'
            outing_request.rejection_reason = rejection_reason
            db.session.commit()
        return redirect(url_for('views.teacher_manage'))
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/delete_user/<string:user_type>/<int:user_id>', methods=['POST'])
def delete_user(user_type, user_id):
    if 'user_id' in session and session['role'] == 'admin':
        admin_password = request.form.get('admin_password')
        admin = Admin.query.get(session['user_id'])

        if not bcrypt.checkpw(admin_password.encode('utf-8'), admin.password.encode('utf-8')):
            flash('비밀번호가 틀렸습니다.')
            return redirect(url_for('views.admin_page'))

        if user_type == 'student':
            user = Student.query.get(user_id)
        elif user_type == 'teacher':
            user = Teacher.query.get(user_id)

        if user:
            db.session.delete(user)
            db.session.commit()
            flash(f'{user_type.capitalize()} with ID {user_id} has been deleted.')
        else:
            flash(f'{user_type.capitalize()} not found.')

        return redirect(url_for('views.admin_page'))
    else:
        flash('Access denied. Admins only.')
        return redirect(url_for('auth.index'))

@views_bp.route('/outing_statistics')
def outing_statistics():
    if 'user_id' in session and session['role'] == 'admin':
        stats = get_outing_statistics()
        grade_stats = []
        for grade in range(1, 4):  # 1학년부터 3학년까지
            grade_count = sum([stat[2] for stat in stats if stat[0] == str(grade)])
            grade_stats.append({'grade': grade, 'count': grade_count})
        return render_template('outing_statistics.html', stats=grade_stats)
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/class_statistics')
def class_statistics():
    grade = request.args.get('grade')
    results = db.session.query(
        Student.student_class, func.count(OutingRequest.id)
    ).join(OutingRequest, Student.name == OutingRequest.student_name) \
        .filter(Student.grade == grade, OutingRequest.status == '승인됨') \
        .group_by(Student.student_class).order_by(Student.student_class).all()

    stats = [{'student_class': r[0], 'count': r[1]} for r in results]
    return jsonify(stats)

@views_bp.route('/student_statistics')
def student_statistics():
    grade = request.args.get('grade')
    student_class = request.args.get('class')

    results = db.session.query(
        Student.name, func.count(OutingRequest.id)
    ).join(OutingRequest, Student.name == OutingRequest.student_name) \
        .filter(Student.grade == grade, Student.student_class == student_class, OutingRequest.status == '승인됨') \
        .group_by(Student.name).order_by(func.count(OutingRequest.id).desc()).all()

    stats = [{'name': r[0], 'count': r[1]} for r in results]
    return jsonify(stats)

@views_bp.route('/delete_all_outing_requests', methods=['POST'])
def delete_all_outing_requests():
    if 'user_id' in session and session['role'] == 'admin':
        admin_password = request.form.get('admin_password')
        admin = Admin.query.get(session['user_id'])

        if not bcrypt.checkpw(admin_password.encode('utf-8'), admin.password.encode('utf-8')):
            flash('비밀번호가 틀렸습니다.')
            return redirect(url_for('views.outing_statistics'))

        OutingRequest.query.delete()
        db.session.commit()
        flash('모든 외출 신청 내역이 삭제되었습니다.')
        return redirect(url_for('views.outing_statistics'))
    else:
        flash('Access denied. Admins only.')
        return redirect(url_for('auth.index'))

@views_bp.route('/manage_account', methods=['GET'])
def manage_account():
    if 'user_id' in session and session['role'] in ['student', 'teacher']:
        conn = get_db_connection()
        user = None
        if session['role'] == 'student':
            user = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()
        elif session['role'] == 'teacher':
            user = conn.execute(text('SELECT * FROM teachers WHERE id = :id'), {'id': session['user_id']}).fetchone()
        user = row_to_dict(user)
        conn.close()
        return render_template('manage_account.html', user=user)
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/validate_password', methods=['POST'])
def validate_password():
    if 'user_id' in session and session['role'] in ['student', 'teacher']:
        password = request.form.get('password')
        conn = get_db_connection()

        user = None
        if session['role'] == 'student':
            user = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()
        elif session['role'] == 'teacher':
            user = conn.execute(text('SELECT * FROM teachers WHERE id = :id'), {'id': session['user_id']}).fetchone()

        user = row_to_dict(user)
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['password_validated'] = True
            flash('비밀번호가 확인되었습니다. 정보를 수정할 수 있습니다.', 'success')
            return render_template('student_home.html',
                                   student=user,
                                   outing_requests=[],
                                   password_validated=True)  # 바로 모달을 열기 위해
        else:
            session['password_validated'] = False
            flash('비밀번호가 일치하지 않습니다. 다시 시도하세요.', 'danger')
            return redirect(url_for('views.student_home'))
    else:
        return redirect(url_for('auth.index'))



@views_bp.route('/update_account', methods=['POST'])
def update_account():
    if 'user_id' in session and session.get('password_validated') and session['role'] in ['student', 'teacher']:
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')

        if new_password and new_password != confirm_password:
            flash('새 비밀번호가 일치하지 않습니다.', 'danger')
            return redirect(url_for('views.student_home'))

        conn = get_db_connection()
        if session['role'] == 'student':
            user = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()
        elif session['role'] == 'teacher':
            user = conn.execute(text('SELECT * FROM teachers WHERE id = :id'), {'id': session['user_id']}).fetchone()

        user = row_to_dict(user)

        if new_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(text('UPDATE students SET password = :password WHERE id = :id' if session[
                                                                                               'role'] == 'student' else 'UPDATE teachers SET password = :password WHERE id = :id'),
                         {'password': hashed_password, 'id': session['user_id']})

        if email:
            conn.execute(text('UPDATE students SET email = :email WHERE id = :id' if session[
                                                                                         'role'] == 'student' else 'UPDATE teachers SET email = :email WHERE id = :id'),
                         {'email': email, 'id': session['user_id']})

        conn.commit()
        conn.close()

        flash('계정 정보가 성공적으로 업데이트되었습니다.', 'success')
        return redirect(url_for('views.student_home'))
    else:
        flash('잘못된 접근입니다.', 'danger')
        return redirect(url_for('auth.index'))


