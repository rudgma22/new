from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import get_db_connection, add_outing_request, approve_outing_request, reject_outing_request, add_extern, get_all_externs, db, Student, Extern, OutingRequest, Teacher  # Teacher 추가
import bcrypt
from sqlalchemy import text
from sqlalchemy.sql import text
from sqlalchemy import func
from datetime import datetime


views_bp = Blueprint('views', __name__)

def row_to_dict(row):
    """SQLAlchemy Row 객체를 딕셔너리로 변환"""
    return {column: getattr(row, column) for column in row._fields}

def get_db_connection():
    return db.session


@views_bp.route('/student_home')
def student_home():
    if 'user_id' in session and session['role'] == 'student':
        conn = get_db_connection()
        student = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()
        student = row_to_dict(student)

        outing_requests = conn.execute(text('SELECT * FROM outing_requests WHERE student_name = :name'),
                                       {'name': student['name']}).fetchall()
        outing_requests = [row_to_dict(request) for request in outing_requests]

        conn.close()

        # 수정: session['password_validated'] 값이 없을 경우 기본값을 False로 설정합니다.
        if 'password_validated' not in session:
            session['password_validated'] = False

        return render_template('student_home.html', student=student, outing_requests=outing_requests,
                               password_validated=session.get('password_validated', False))
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/teacher_home')
def teacher_home():
    if 'user_id' in session and session['role'] == 'teacher':
        conn = get_db_connection()
        teacher = conn.execute(text('SELECT * FROM teachers WHERE id = :id'), {'id': session['user_id']}).fetchone()
        teacher = row_to_dict(teacher)

        new_requests_only = request.args.get('new_requests_only', 'false').lower() == 'true'
        if new_requests_only:
            outing_requests = conn.execute(text(
                'SELECT o.id, s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count, '
                'o.status '
                'FROM outing_requests o '
                'JOIN students s ON o.barcode = s.barcode '
                'WHERE o.status = "대기중" AND s.grade = :grade AND s.student_class = :class '
                'ORDER BY s.number'),
                {'grade': teacher['grade'], 'class': teacher['teacher_class']}).fetchall()
        else:
            outing_requests = conn.execute(text(
                'SELECT s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                '(SELECT COUNT(*) FROM outing_requests o WHERE o.barcode = s.barcode AND o.status = "승인됨") as outing_count '
                'FROM students s '
                'LEFT JOIN outing_requests o ON s.barcode = o.barcode '
                'WHERE s.grade = :grade AND s.student_class = :class '
                'GROUP BY s.id, s.grade, s.student_class, s.number, s.name '
                'ORDER BY s.number'),
                {'grade': teacher['grade'], 'class': teacher['teacher_class']}).fetchall()

        outing_requests = [row_to_dict(request) for request in outing_requests]
        externs = Extern.query.all()
        extern_ids = [extern.student_id for extern in externs]

        conn.close()

        # 수정: session['password_validated'] 값이 없을 경우 기본값을 False로 설정합니다.
        if 'password_validated' not in session:
            session['password_validated'] = False

        return render_template('teacher_home.html', teacher=teacher, outing_requests=outing_requests,
                               externs=externs, extern_ids=extern_ids,
                               new_requests_only=new_requests_only,
                               password_validated=session.get('password_validated', False))
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
                if not student_id:
                    print(f"Invalid student ID: {student_id}")
                    return jsonify({'status': 'error', 'message': 'Invalid student ID'}), 400

                student = Student.query.get(student_id)
                if not student:
                    print(f"Invalid student ID: {student_id}")
                    return jsonify({'status': 'error', 'message': 'Invalid student ID'}), 400

                # 이미 지정된 통학생인지 확인
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
            print("Invalid action:", action)
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
            # 교사가 담당하는 학년/반의 대기중인 모든 외출 신청을 승인
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
        conn = get_db_connection()
        student = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()

        if student is not None:
            student = row_to_dict(student)
        else:
            flash('학생 정보를 가져올 수 없습니다.', 'danger')
            return redirect(url_for('views.student_home'))

        existing_request = conn.execute(text(
            'SELECT * FROM outing_requests WHERE student_name = :name AND status = "대기중"'),
            {'name': student['name']}
        ).fetchone()

        if existing_request is not None:
            existing_request = row_to_dict(existing_request)

        if not existing_request:
            start_time_str = request.form['start_time']
            end_time_str = request.form['end_time']
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            reason = request.form['reason']

            grade = student.get('grade')
            student_class = student.get('student_class')

            if grade is None or student_class is None:
                flash('학생의 학년 또는 반 정보를 찾을 수 없습니다.', 'danger')
                return redirect(url_for('views.student_home'))

            new_request = OutingRequest(
                student_name=student['name'],
                barcode=student['barcode'],
                grade=grade,
                student_class=student_class,
                start_time=start_time,
                end_time=end_time,
                reason=reason,
                status='대기중'
            )
            conn.add(new_request)
            conn.commit()
            flash('외출 신청이 성공적으로 접수되었습니다.', 'success')
        else:
            flash('이미 대기 중인 외출 신청이 있습니다.', 'warning')

        conn.close()
        return redirect(url_for('views.student_home'))
    else:
        return redirect(url_for('auth.index'))

from flask import request  # Ensure this import statement is present

@views_bp.route('/reject_leave/<int:request_id>', methods=['POST'])
def reject_leave(request_id):
    # Make sure to use Flask's request object
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
        password = request.form['password']
        role = session['role']

        conn = get_db_connection()
        user = None
        if role == 'student':
            user = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()
        elif role == 'teacher':
            user = conn.execute(text('SELECT * FROM teachers WHERE id = :id'), {'id': session['user_id']}).fetchone()

        user = row_to_dict(user)
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
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
    if 'user_id' in session and session.get('password_validated'):
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')

        if new_password and new_password == confirm_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            flash('비밀번호가 일치하지 않거나 유효하지 않습니다.')
            return redirect(
                url_for('views.teacher_home') if session['role'] == 'teacher' else url_for('views.student_home'))

        conn = get_db_connection()
        if session['role'] == 'student':
            conn.execute(text('UPDATE students SET password = :password, email = :email WHERE id = :id'),
                         {'password': hashed_password, 'email': email, 'id': session['user_id']})
        elif session['role'] == 'teacher':
            conn.execute(text('UPDATE teachers SET password = :password, email = :email WHERE id = :id'),
                         {'password': hashed_password, 'email': email, 'id': session['user_id']})

        conn.commit()
        conn.close()

        session.pop('password_validated', None)
        flash('계정 정보가 성공적으로 업데이트되었습니다.')
        return redirect(
            url_for('views.teacher_home') if session['role'] == 'teacher' else url_for('views.student_home'))
    else:
        flash('비밀번호 검증이 필요합니다.')
        return redirect(
            url_for('views.teacher_home') if session['role'] == 'teacher' else url_for('views.student_home'))