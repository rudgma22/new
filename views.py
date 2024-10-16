from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, make_response, request
from flask_socketio import emit
from models import db, Student, Extern, OutingRequest, Teacher, Notice
import bcrypt
from sqlalchemy import text
from datetime import datetime
from werkzeug.security import generate_password_hash
from flask import current_app

# 블루프린트 정의
views_bp = Blueprint('views', __name__, url_prefix='/views')

def row_to_dict(row):
    if isinstance(row, dict):
        return row
    if hasattr(row, '_fields'):
        return {field: getattr(row, field) for field in row._fields}
    elif hasattr(row, '__table__'):
        return {column.name: getattr(row, column.name) for column in row.__table__.columns}
    else:
        raise ValueError("Unsupported row type")


@views_bp.route('/logout')
def logout():
    session.clear()  # 세션에서 모든 데이터 삭제
    response = make_response(redirect(url_for('auth.index')))
    # 캐시 무효화 헤더 추가
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@views_bp.route('/get_notices', methods=['GET'])
def get_notices():
    notices = Notice.query.filter(
        Notice.post_date <= datetime.now(),
        Notice.expiration_date >= datetime.now()
    ).order_by(Notice.post_date.desc()).all()

    notice_list = [
        {'title': notice.title, 'content': notice.content, 'post_date': notice.post_date.strftime('%Y-%m-%d')}
        for notice in notices
    ]
    return jsonify(notice_list)


@views_bp.route('/add_notice')
def add_notice():
    # 공지사항 작성 페이지를 렌더링
    return render_template('add_notice.html')

@views_bp.route('/submit_notice', methods=['POST'])
def submit_notice():
    title = request.form.get('title')
    content = request.form.get('content')
    post_date = datetime.strptime(request.form.get('post_date'), '%Y-%m-%dT%H:%M')
    expiration_date = datetime.strptime(request.form.get('expiration_date'), '%Y-%m-%dT%H:%M')

    if title and content:
        new_notice = Notice(title=title, content=content, post_date=post_date, expiration_date=expiration_date)
        db.session.add(new_notice)
        db.session.commit()

        flash('공지사항이 성공적으로 등록되었습니다.', 'success')
        return redirect(url_for('views.add_notice'))
    else:
        flash('모든 필드를 채워주세요.', 'danger')
        return redirect(url_for('views.add_notice'))


@views_bp.route('/student_home')
def student_home():
    # 로그인 세션 확인
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('auth.index'))

    # 현재 로그인된 학생 정보 가져오기
    student = Student.query.get(session['user_id'])

    # 'hide_notice' 쿠키가 없을 경우 공지사항을 가져옴
    if 'hide_notice' not in request.cookies:
        notice = Notice.query.filter(
            Notice.post_date <= datetime.now(),
            Notice.expiration_date >= datetime.now()
        ).order_by(Notice.post_date.desc()).first()
    else:
        notice = None  # 쿠키가 있으면 공지사항을 표시하지 않음

    # 학생이 있는 경우 외출 요청 목록 가져오기
    if student:
        outing_requests = OutingRequest.query.filter_by(student_name=student.name).all()

        # 외출 요청 시간 형식 변환
        for req in outing_requests:
            req.start_time = req.start_time.strftime('%Y-%m-%d %H:%M')
            req.end_time = req.end_time.strftime('%Y-%m-%d %H:%M')

        # 페이지 렌더링 및 응답 생성
        response = make_response(render_template(
            'student_home.html',
            student=row_to_dict(student),  # 학생 정보
            outing_requests=[row_to_dict(req) for req in outing_requests],  # 외출 요청 목록
            notice=notice  # 공지사항 (쿠키에 따라 표시될지 결정됨)
        ))

        # 캐시 무효화 헤더 추가
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'

        return response
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/teacher_home')
def teacher_home():
    if 'user_id' not in session or session['role'] != 'teacher':
        return redirect(url_for('auth.index'))

    teacher = Teacher.query.get(session['user_id'])

    # 쿠키를 통해 '하루 동안 보지 않기' 설정 확인
    if 'hide_notice' not in request.cookies:
        # 공지사항을 조회, 현재 시간에 유효한 공지사항만 가져옴
        notice = Notice.query.filter(
            Notice.post_date <= datetime.now(),
            Notice.expiration_date >= datetime.now()
        ).order_by(Notice.post_date.desc()).first()
    else:
        notice = None

    if teacher:
        new_requests_only = request.args.get('new_requests_only', 'false').lower() == 'true'

        # '학년'과 '반'이 모두 '기타'인 경우 모든 학생을 표시
        if teacher.grade == '기타' and teacher.teacher_class == '기타':
            if new_requests_only:
                outing_requests = db.session.execute(text(
                    'SELECT o.id, s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                    '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count, '
                    'o.start_time, o.end_time, o.status, o.reason '
                    'FROM outing_requests o '
                    'JOIN students s ON o.barcode = s.barcode '
                    'WHERE o.status = "대기중" '
                    'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'
                )).fetchall()
            else:
                outing_requests = db.session.execute(text(
                    'SELECT s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                    'MAX(o.reason) as reason, '
                    '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count '
                    'FROM students s '
                    'LEFT JOIN outing_requests o ON s.barcode = o.barcode '
                    'GROUP BY s.id, s.grade, s.student_class, s.number, s.name '
                    'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'
                )).fetchall()
        else:
            # 기존 로직: 특정 학년/반에 대한 처리
            if teacher.teacher_class == '기타':
                if new_requests_only:
                    outing_requests = db.session.execute(text(
                        'SELECT o.id, s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                        '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count, '
                        'o.start_time, o.end_time, o.status, o.reason '
                        'FROM outing_requests o '
                        'JOIN students s ON o.barcode = s.barcode '
                        'WHERE o.status = "대기중" AND s.grade = :grade '
                        'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'),
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
                        'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'),
                        {'grade': teacher.grade}).fetchall()
            else:
                if new_requests_only:
                    outing_requests = db.session.execute(text(
                        'SELECT o.id, s.id as student_id, s.grade, s.student_class, s.number, s.name as student_name, '
                        '(SELECT COUNT(*) FROM outing_requests o2 WHERE o2.barcode = s.barcode AND o2.status = "승인됨") as outing_count, '
                        'o.start_time, o.end_time, o.status, o.reason '
                        'FROM outing_requests o '
                        'JOIN students s ON o.barcode = s.barcode '
                        'WHERE o.status = "대기중" AND s.grade = :grade AND s.student_class = :class '
                        'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'),
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
                        'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'),
                        {'grade': teacher.grade, 'class': teacher.teacher_class}).fetchall()

        outing_requests = [row_to_dict(outing_request) for outing_request in outing_requests]

        # 날짜 형식 변환
        for outing_request in outing_requests:
            if 'start_time' in outing_request and outing_request['start_time']:
                outing_request['start_time'] = outing_request['start_time'].strftime('%Y-%m-%d %H:%M')
            if 'end_time' in outing_request and outing_request['end_time']:
                outing_request['end_time'] = outing_request['end_time'].strftime('%Y-%m-%d %H:%M')

        # '학년'과 '반'이 모두 '기타'인 경우 모든 externs 가져오기
        if teacher.grade == '기타' and teacher.teacher_class == '기타':
            externs = db.session.execute(text(
                'SELECT e.* '
                'FROM externs e '
                'JOIN students s ON e.student_id = s.id '
                'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'
            )).fetchall()
        else:
            if teacher.teacher_class == '기타':
                externs = db.session.execute(text(
                    'SELECT e.* '
                    'FROM externs e '
                    'JOIN students s ON e.student_id = s.id '
                    'WHERE s.grade = :grade '
                    'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'),
                    {'grade': teacher.grade}).fetchall()
            else:
                externs = db.session.execute(text(
                    'SELECT e.* '
                    'FROM externs e '
                    'JOIN students s ON e.student_id = s.id '
                    'WHERE s.grade = :grade AND s.student_class = :class '
                    'ORDER BY s.grade, CAST(s.student_class AS UNSIGNED), CAST(s.number AS UNSIGNED)'),
                    {'grade': teacher.grade, 'class': teacher.teacher_class}).fetchall()

        externs = [row_to_dict(extern) for extern in externs]

        response = make_response(render_template(
            'teacher_home.html',
            teacher=row_to_dict(teacher),
            outing_requests=outing_requests,
            externs=externs,
            notice=notice,  # 공지사항 추가
            new_requests_only=new_requests_only
        ))
        # 캐시 무효화 헤더 추가
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/admin_home')
def admin_home():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('auth.index'))

    response = make_response(render_template('admin_page.html'))
    # 캐시 무효화 헤더 추가
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


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
            for extern_id in extern_ids:
                extern = Extern.query.get(extern_id)
                if extern:
                    db.session.delete(extern)
                else:
                    print(f"Extern not found for ID: {extern_id}")
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
            if teacher.grade == '기타' and teacher.teacher_class == '기타':
                # 모든 외출 신청을 승인
                requests_to_approve = OutingRequest.query.filter_by(status='대기중').all()
            else:
                # 기존 로직
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

@views_bp.route('/apply_leave', methods=['POST'])
def apply_leave():
    if 'user_id' in session and session['role'] == 'student':
        student = Student.query.get(session['user_id'])

        if student is not None:
            existing_request = OutingRequest.query.filter_by(student_name=student.name, status="대기중").first()

            # 이미 대기 중인 외출 신청이 있는 경우
            if existing_request:
                flash('이미 대기 중인 외출이 있습니다.', 'danger')  # 'danger' 카테고리로 변경
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

            notify_teachers(student.grade, student.student_class)

            flash('외출 신청이 성공적으로 접수되었습니다.', 'success')
            return redirect(url_for('views.student_home'))
        else:
            flash('학생 정보를 가져올 수 없습니다.', 'danger')
            return redirect(url_for('views.student_home'))
    else:
        return redirect(url_for('auth.index'))


def notify_teachers(grade, student_class):
    socketio = current_app.extensions['socketio']
    socketio.emit('new_outing_request', {'grade': grade, 'class': student_class}, namespace='/teachers_notifications')


@views_bp.route('/cancel_leave/<int:request_id>', methods=['POST'])
def cancel_leave(request_id):
    try:
        # 외출 신청을 찾고 삭제
        outing_request = OutingRequest.query.get(request_id)
        if outing_request and outing_request.status == '대기중':
            db.session.delete(outing_request)
            db.session.commit()
            return jsonify({'status': 'success', 'message': '외출 신청이 취소되었습니다.'}), 200
        else:
            return jsonify({'status': 'error', 'message': '취소할 외출 신청을 찾을 수 없습니다.'}), 404
    except Exception as e:
        print(f"Error occurred during leave cancellation: {e}")
        return jsonify({'status': 'error', 'message': '서버 오류가 발생했습니다.'}), 500

@views_bp.route('/approve_leave/<int:request_id>', methods=['POST'])
def approve_leave(request_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    try:
        request = OutingRequest.query.get(request_id)
        if request:
            request.status = '승인됨'
            approver_name = Teacher.query.get(session['user_id']).name  # 승인자의 username 가져오기
            request.approver = approver_name  # 승인자 username 저장
            db.session.commit()
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
    except Exception as e:
        print(f"Error occurred during leave approval: {e}")
        return jsonify({'status': 'error', 'message': 'Server error'}), 500


@views_bp.route('/reject_leave/<int:request_id>', methods=['POST'])
def reject_leave(request_id):
    json_data = request.get_json()
    rejection_reason = json_data.get('rejection_reason', '')

    try:
        outing_request = OutingRequest.query.get(request_id)
        if outing_request:
            outing_request.status = '거절됨'
            approver_name = Teacher.query.get(session['user_id']).name
            outing_request.approver = approver_name
            outing_request.rejection_reason = rejection_reason
            db.session.commit()
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
    except Exception as e:
        print(f"Error occurred during leave rejection: {e}")
        return jsonify({'status': 'error', 'message': 'Server error'}), 500


@views_bp.route('/get_approved_outings', methods=['GET'])
def get_approved_outings():
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    teacher = Teacher.query.get(session['user_id'])

    try:
        # 기본 쿼리: 승인 또는 거절된 외출 신청
        query = db.session.query(OutingRequest, Student).join(Student, OutingRequest.barcode == Student.barcode) \
            .filter(OutingRequest.status.in_(['승인됨', '거절됨'])) \
            .filter(OutingRequest.approver == teacher.name)  # 현재 로그인한 교사의 승인/거절 내역만 필터링

        # 학년이 기타일 경우 전체 학년, 그렇지 않으면 특정 학년을 필터링
        if teacher.grade != '기타':
            query = query.filter(Student.grade == teacher.grade)

        # 반이 기타일 경우 전체 반, 그렇지 않으면 특정 반을 필터링
        if teacher.teacher_class != '기타':
            query = query.filter(Student.student_class == teacher.teacher_class)

        # 관리용계정은 다른 사용자에게 표시되지 않도록 필터링
        if teacher.name != '관리용계정':
            query = query.filter(OutingRequest.approver != '관리용계정')

        approved_outings = query.all()

        # 승인된 외출 내역 리스트 생성
        approved_outings_list = [
            {
                'name': outing_request.student_name,
                'grade': student.grade,
                'student_class': student.student_class,
                'number': student.number,
                'start_time': outing_request.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': outing_request.end_time.strftime('%Y-%m-%d %H:%M'),
                'status': outing_request.status,  # 상태 포함
                'approver': outing_request.approver
            } for outing_request, student in approved_outings
        ]

        return jsonify(approved_outings_list), 200

    except Exception as e:
        print(f"Error fetching approved outings: {e}")
        return jsonify({'status': 'error', 'message': 'Server error'}), 500


@views_bp.route('/validate_password', methods=['POST'])
def validate_password():
    if 'user_id' in session:
        password = request.form.get('password')
        if not password:
            flash('비밀번호를 입력해주세요.', 'danger')  # 플래시 메시지로 응답
            return redirect(url_for('views.student_home'))

        role = session['role']
        user = None
        if role == 'student':
            user = Student.query.get(session['user_id'])
        elif role == 'teacher':
            user = Teacher.query.get(session['user_id'])

        # 비밀번호 검증
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            session['password_validated'] = True
            return redirect(url_for('views.student_home'))  # 성공 시 리다이렉트만 수행
        else:
            flash('비밀번호가 일치하지 않습니다.', 'danger')  # 비밀번호 오류 시 플래시 메시지
            return redirect(url_for('views.student_home'))  # 필요에 따라 다른 URL로 리다이렉트 가능
    else:
        flash('인증되지 않은 사용자입니다.', 'danger')  # 세션에 user_id가 없을 경우
        return redirect(url_for('auth.index'))



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


@views_bp.route('/check_new_requests', methods=['GET'])
def check_new_requests():
    if 'user_id' not in session or session['role'] != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 401

    teacher = Teacher.query.get(session['user_id'])
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404

    if teacher.teacher_class == '기타':
        new_requests = OutingRequest.query.filter_by(
            grade=teacher.grade,
            status='대기중'
        ).count()
    else:
        new_requests = OutingRequest.query.filter_by(
            grade=teacher.grade,
            student_class=teacher.teacher_class,
            status='대기중'
        ).count()

    return jsonify({'new_requests': new_requests > 0})