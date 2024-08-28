from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, Student, Extern, OutingRequest, Teacher  # 필요한 모델들 임포트
import bcrypt
from sqlalchemy import text
from datetime import datetime
from werkzeug.security import generate_password_hash

views_bp = Blueprint('views', __name__)


def row_to_dict(row):
    # If row is a dictionary, return it as is
    if isinstance(row, dict):
        return row

    # If row is an SQLAlchemy RowProxy (from raw SQL), convert it to a dictionary
    if hasattr(row, '_fields'):
        return {field: getattr(row, field) for field in row._fields}

    # If row is an SQLAlchemy ORM object, convert it to a dictionary
    elif hasattr(row, '__table__'):
        return {column.name: getattr(row, column.name) for column in row.__table__.columns}

    else:
        raise ValueError("Unsupported row type")



@views_bp.route('/student_home')
def student_home():
    if 'user_id' in session and session['role'] == 'student':
        student = Student.query.get(session['user_id'])
        if student:
            outing_requests = OutingRequest.query.filter_by(student_name=student.name).all()

            # 날짜와 시간을 포맷팅합니다.
            for request in outing_requests:
                request.start_time = request.start_time.strftime('%Y-%m-%d %H:%M')
                request.end_time = request.end_time.strftime('%Y-%m-%d %H:%M')

            if 'password_validated' not in session:
                session['password_validated'] = False

            return render_template('student_home.html', student=row_to_dict(student),
                                   outing_requests=[row_to_dict(req) for req in outing_requests],
                                   password_validated=session.get('password_validated', False))
        else:
            return redirect(url_for('auth.index'))
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/teacher_home')
def teacher_home():
    if 'user_id' in session and session['role'] == 'teacher':
        teacher = Teacher.query.get(session['user_id'])
        if teacher:
            new_requests_only = request.args.get('new_requests_only', 'false').lower() == 'true'

            # 교사가 '기타' 반인 경우의 쿼리 수정
            if teacher.teacher_class == '기타':
                if new_requests_only:
                    outing_requests = db.session.execute(text(
                        'SELECT o.id, s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                        '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count, '
                        'o.status, o.reason '
                        'FROM outing_requests o '
                        'JOIN students s ON o.barcode = s.barcode '
                        'WHERE o.status = "대기중" AND s.grade = :grade '
                        'ORDER BY s.student_class, s.number'),
                        {'grade': teacher.grade}).fetchall()
                else:
                    outing_requests = db.session.execute(text(
                        'SELECT s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                        'MAX(o.reason) as reason, '
                        '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count '
                        'FROM students s '
                        'LEFT JOIN outing_requests o ON s.barcode = o.barcode '
                        'WHERE s.grade = :grade '
                        'GROUP BY s.id, s.grade, s.student_class, s.number, s.name '
                        'ORDER BY s.student_class, s.number'),
                        {'grade': teacher.grade}).fetchall()
            else:
                # 기존 쿼리 유지
                if new_requests_only:
                    outing_requests = db.session.execute(text(
                        'SELECT o.id, s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                        '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count, '
                        'o.status, o.reason '
                        'FROM outing_requests o '
                        'JOIN students s ON o.barcode = s.barcode '
                        'WHERE o.status = "대기중" AND s.grade = :grade AND s.student_class = :class '
                        'ORDER BY s.number'),
                        {'grade': teacher.grade, 'class': teacher.teacher_class}).fetchall()
                else:
                    outing_requests = db.session.execute(text(
                        'SELECT s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                        'MAX(o.reason) as reason, '
                        '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count '
                        'FROM students s '
                        'LEFT JOIN outing_requests o ON s.barcode = o.barcode '
                        'WHERE s.grade = :grade AND s.student_class = :class '
                        'GROUP BY s.id, s.grade, s.student_class, s.number, s.name '
                        'ORDER BY s.number'),
                        {'grade': teacher.grade, 'class': teacher.teacher_class}).fetchall()

            outing_requests = [row_to_dict(request) for request in outing_requests]

            # 통학생 조회 로직도 수정
            if teacher.teacher_class == '기타':
                externs = db.session.execute(text(
                    'SELECT e.* '
                    'FROM externs e '
                    'JOIN students s ON e.student_id = s.id '
                    'WHERE s.grade = :grade'),
                    {'grade': teacher.grade}).fetchall()
            else:
                externs = db.session.execute(text(
                    'SELECT e.* '
                    'FROM externs e '
                    'JOIN students s ON e.student_id = s.id '
                    'WHERE s.grade = :grade AND s.student_class = :class'),
                    {'grade': teacher.grade, 'class': teacher.teacher_class}).fetchall()

            externs = [row_to_dict(extern) for extern in externs]

            if 'password_validated' not in session:
                session['password_validated'] = False

            return render_template('teacher_home.html', teacher=row_to_dict(teacher), outing_requests=outing_requests,
                                   externs=externs, new_requests_only=new_requests_only,
                                   password_validated=session.get('password_validated', False))
        else:
            return redirect(url_for('auth.index'))
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/admin_home')
def admin_home():
    if 'user_id' in session and session['role'] == 'admin':
        return render_template('admin_page.html')
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/add_extern', methods=['POST'])
def add_extern():
    data = request.get_json()
    extern_ids = data.get('externs', [])
    action = data.get('action', '')

    if not extern_ids or not isinstance(extern_ids, list):
        return jsonify({'status': 'error', 'message': 'Invalid data format'}), 400

    try:
        if action == 'add':
            for student_id in extern_ids:
                student = Student.query.get(student_id)
                if not student:
                    return jsonify({'status': 'error', 'message': f'Invalid student ID: {student_id}'}), 400

                if not Extern.query.filter_by(student_id=student.id).first():
                    extern = Extern(
                        student_id=student.id,
                        name=student.name,
                        grade=student.grade,
                        student_class=student.student_class,
                        number=student.number,
                        barcode=student.barcode
                    )
                    db.session.add(extern)
                else:
                    print(f"Student ID {student_id} is already an extern.")
        elif action == 'remove':
            for student_id in extern_ids:
                extern = Extern.query.filter_by(student_id=student_id).first()
                if extern:
                    db.session.delete(extern)
                else:
                    print(f"Extern not found for student ID: {student_id}")
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400

        db.session.commit()
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error occurred during add_extern processing: {e}")
        return jsonify({'status': 'error', 'message': 'Server error'}), 500


@views_bp.route('/bulk_approve', methods=['POST'])
def bulk_approve():
    if 'user_id' in session and session['role'] == 'teacher':
        try:
            teacher = Teacher.query.get(session['user_id'])
            requests_to_approve = OutingRequest.query.filter_by(
                grade=teacher.grade,
                student_class=teacher.teacher_class,
                status='대기중'
            ).all()

            if not requests_to_approve:
                return jsonify({'status': 'no_requests', 'message': '승인할 학생이 없습니다.'}), 200

            for request in requests_to_approve:
                request.status = '승인됨'

            db.session.commit()
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            db.session.rollback()
            print(f"Error occurred during bulk approval: {e}")
            return jsonify({'status': 'error', 'message': 'Server error'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403


@views_bp.route('/approve_leave/<int:request_id>', methods=['POST'])
def approve_leave(request_id):
    try:
        request = OutingRequest.query.get(request_id)
        if request:
            request.status = '승인됨'
            db.session.commit()
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
    except Exception as e:
        print(f"Error occurred during leave approval: {e}")
        return jsonify({'status': 'error', 'message': 'Server error'}), 500


@views_bp.route('/apply_leave', methods=['POST'])
def apply_leave():
    if 'user_id' in session and session['role'] == 'student':
        student = Student.query.get(session['user_id'])

        if student is not None:
            existing_request = OutingRequest.query.filter_by(student_name=student.name, status="대기중").first()

            if existing_request:
                flash('이미 대기 중인 외출 신청이 있습니다.', 'warning')
                return redirect(url_for('views.student_home'))

            start_time_str = request.form['start_time']
            end_time_str = request.form['end_time']
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')

            reason = request.form.get('reason', '기타')
            if reason == '기타':
                reason = request.form.get('other_reason', '기타')

            new_request = OutingRequest(
                student_name=student.name,
                barcode=student.barcode,
                grade=student.grade,
                student_class=student.student_class,
                start_time=start_time,
                end_time=end_time,
                reason=reason,
                status='대기중'
            )

            db.session.add(new_request)
            db.session.commit()
            flash('외출 신청이 성공적으로 접수되었습니다.', 'success')
            return redirect(url_for('views.student_home'))
        else:
            flash('학생 정보를 가져올 수 없습니다.', 'danger')
            return redirect(url_for('views.student_home'))
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/reject_leave/<int:request_id>', methods=['POST'])
def reject_leave(request_id):
    json_data = request.get_json()
    rejection_reason = json_data.get('rejection_reason', '')

    try:
        outing_request = OutingRequest.query.get(request_id)
        if outing_request:
            outing_request.status = '거절됨'
            outing_request.rejection_reason = rejection_reason
            db.session.commit()
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
    except Exception as e:
        print(f"Error occurred during leave rejection: {e}")
        return jsonify({'status': 'error', 'message': 'Server error'}), 500


@views_bp.route('/validate_password', methods=['POST'])
def validate_password():
    if 'user_id' in session:
        password = request.form.get('password')
        if not password:
            return jsonify({'status': 'error', 'message': '비밀번호를 입력해주세요.'}), 400

        role = session['role']
        user = None
        if role == 'student':
            user = Student.query.get(session['user_id'])
        elif role == 'teacher':
            user = Teacher.query.get(session['user_id'])

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            session['password_validated'] = True
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': '비밀번호가 일치하지 않습니다.'}), 400
    else:
        return jsonify({'status': 'error', 'message': '인증되지 않은 사용자입니다.'}), 403


@views_bp.route('/reset_password_validation', methods=['POST'])
def reset_password_validation():
    """Reset the password validation state in the session."""
    session['password_validated'] = False
    return jsonify({'status': 'success'}), 200


@views_bp.route('/update_account', methods=['POST'])
def update_account():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))

    user_id = session['user_id']
    user_role = session['role']

    if user_role == 'student':
        user = Student.query.get(user_id)
        user_table = Student
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
        user_table = Teacher
    else:
        return jsonify({'status': 'danger', 'message': '잘못된 사용자 유형입니다.'})

    if user is None:
        return jsonify({'status': 'danger', 'message': '사용자 정보를 가져올 수 없습니다.'})

    new_email = request.form.get('email')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not new_email or '@' not in new_email:
        return jsonify({'status': 'danger', 'message': '유효하지 않은 이메일 주소입니다.'})

    existing_user = user_table.query.filter(user_table.email == new_email, user_table.id != user_id).first()

    if existing_user:
        return jsonify({'status': 'danger', 'message': '중복된 이메일이 있습니다.'})

    if new_password and new_password != confirm_password:
        return jsonify({'status': 'danger', 'message': '비밀번호가 일치하지 않습니다.'})

    try:
        if new_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user.password = hashed_password

        user.email = new_email
        db.session.commit()
        return jsonify({'status': 'success', 'message': '정보가 성공적으로 업데이트되었습니다.'})

    except Exception as e:
        db.session.rollback()
        print(f"Error updating account: {e}")
        return jsonify({'status': 'danger', 'message': '서버 오류가 발생했습니다. 다시 시도해주세요.'})


@views_bp.route('/get_users', methods=['GET'])
def get_users():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401

    user_type = request.args.get('type', 'student')
    user_id = request.args.get('id')

    grade = request.args.get('grade')
    student_class = request.args.get('class')
    number = request.args.get('number')

    if user_id:
        if user_type == 'student':
            user = Student.query.get(user_id)
        elif user_type == 'teacher':
            user = Teacher.query.get(user_id)
        else:
            return jsonify({'error': 'Invalid user type'}), 400

        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_data = {
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'grade': user.grade,
            'class': user.student_class if user_type == 'student' else user.teacher_class,
            'number': user.number if user_type == 'student' else '',
            'barcode': user.barcode if user_type == 'student' else ''
        }

        return jsonify(user_data)

    else:
        query = None
        if user_type == 'student':
            query = Student.query
            if grade:
                query = query.filter_by(grade=grade)
            if student_class:
                query = query.filter_by(student_class=student_class)
            if number:
                query = query.filter_by(number=number)
        elif user_type == 'teacher':
            query = Teacher.query
            if grade:
                query = query.filter_by(grade=grade)
            if student_class:
                query = query.filter_by(teacher_class=student_class)
        else:
            return jsonify({'error': 'Invalid user type'}), 400

        users = query.all()
        user_list = []
        for user in users:
            user_data = {
                'id': user.id,
                'name': user.name,
                'username': user.username,
                'grade': user.grade,
                'class': user.student_class if user_type == 'student' else user.teacher_class,
                'number': user.number if user_type == 'student' else ''
            }
            user_list.append(user_data)

        return jsonify(user_list)



@views_bp.route('/update_user', methods=['POST'])
def update_user():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    user_type = data.get('type')
    user_id = data.get('id')

    if user_type == 'student':
        user = Student.query.get(user_id)
    elif user_type == 'teacher':
        user = Teacher.query.get(user_id)
    else:
        return jsonify({'error': 'Invalid user type'}), 400

    if user:
        user.name = data.get('name')
        user.grade = data.get('grade')
        if user_type == 'student':
            user.student_class = data.get('class')
            user.number = data.get('number')
            user.barcode = data.get('barcode')
        else:
            user.teacher_class = data.get('class')

        db.session.commit()
        return jsonify({'success': True, 'message': '사용자 정보가 업데이트되었습니다.'})
    else:
        return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404


@views_bp.route('/delete_user', methods=['POST'])
def delete_user():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    user_type = data.get('type')
    user_id = data.get('id')

    if user_type == 'student':
        user = Student.query.get(user_id)
    elif user_type == 'teacher':
        user = Teacher.query.get(user_id)
    else:
        return jsonify({'error': 'Invalid user type'}), 400

    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': '사용자가 삭제되었습니다.'})
    else:
        return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
