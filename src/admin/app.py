from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.routing import BaseConverter
from dotenv import load_dotenv
import os
import sys
import logging

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import get_db_connection, get_user_challenges, update_challenge_admin
from admin.auth import login_required, verify_password
from config import BotStates, STATE_KOREAN, VALID_STATES, normalize_state, env_to_bool

class BigIntConverter(BaseConverter):
    """64비트 정수를 처리하는 커스텀 URL 컨버터 (Discord user_id 등)"""
    regex = r'\d+'

    def to_python(self, value):
        """URL에서 Python 객체로 변환"""
        return int(value)

    def to_url(self, value):
        """Python 객체에서 URL로 변환"""
        return str(value)

app = Flask(__name__)
flask_secret_key = os.getenv('FLASK_SECRET_KEY')
if not flask_secret_key or flask_secret_key == 'your-random-secret-key-here':
    raise RuntimeError("FLASK_SECRET_KEY가 안전한 값으로 설정되어야 합니다.")
app.secret_key = flask_secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = env_to_bool('SESSION_COOKIE_SECURE', False)

logger = logging.getLogger(__name__)

# 커스텀 URL 컨버터 등록
app.url_map.converters['bigint'] = BigIntConverter

@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    if request.method == 'POST':
        password = request.form.get('password')
        if verify_password(password):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('비밀번호가 틀렸습니다.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """로그아웃"""
    session.pop('logged_in', None)
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    """루트 경로 - 로그인 여부에 따라 리다이렉트"""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """대시보드 메인"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM users")
        total_users = c.fetchone()['total']
        c.execute("SELECT SUM(ducks_raised) as total FROM users")
        total_ducks = c.fetchone()['total'] or 0
        c.execute("SELECT COUNT(*) as total FROM duck_challenge")
        total_challenges = c.fetchone()['total']

    return render_template('dashboard.html',
                          total_users=total_users,
                          total_ducks=total_ducks,
                          total_challenges=total_challenges)

@app.route('/users')
@login_required
def users_list():
    """유저 목록"""
    search = request.args.get('search', '')
    with get_db_connection() as conn:
        c = conn.cursor()
        if search:
            c.execute('''
                SELECT * FROM users
                WHERE username LIKE ? OR CAST(user_id AS TEXT) LIKE ?
                ORDER BY ducks_raised DESC
            ''', (f'%{search}%', f'%{search}%'))
        else:
            c.execute('SELECT * FROM users ORDER BY ducks_raised DESC')
        users = [dict(row) for row in c.fetchall()]
    return render_template('users.html', users=users, search=search)

@app.route('/users/<bigint:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """유저 정보 수정"""
    if request.method == 'POST':
        # 유저 기본 정보 업데이트
        gold = int(request.form.get('gold', 0))
        ducks_raised = int(request.form.get('ducks_raised', 0))

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE users
                SET gold = ?, ducks_raised = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (gold, ducks_raised, user_id))

        # 도전 정보 업데이트 (있는 경우)
        challenge_id = request.form.get('challenge_id')
        if challenge_id:
            # 상태 값 검증
            state = request.form.get('state')
            if state not in VALID_STATES:
                flash(f'유효하지 않은 상태값: {state}', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
            
            streak = int(request.form.get('streak', 0))
            growth_days = int(request.form.get('growth_days', 0))
            total_days = int(request.form.get('total_days', 0))
            
            # 음수 검증
            if streak < 0 or growth_days < 0 or total_days < 0:
                flash('연속 일수, 성장일, 총 일수는 0 이상이어야 합니다.', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
            
            success = update_challenge_admin(
                thread_id=int(challenge_id),
                state=state,
                streak=streak,
                growth_days=growth_days,
                total_days=total_days
            )
            
            if not success:
                flash('도전 정보 업데이트에 실패했습니다.', 'warning')

        flash('유저 정보가 업데이트되었습니다.', 'success')
        return redirect(url_for('users_list'))

    # GET 요청: 유저 정보 및 활성 도전 조회
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = c.fetchone()
        if not user_row:
            flash('유저를 찾을 수 없습니다.', 'error')
            return redirect(url_for('users_list'))
        user = dict(user_row)
    
    # 활성 도전 조회 (가장 최근 것)
    challenges = get_user_challenges(user_id)
    active_challenge = challenges[0] if challenges else None
    if active_challenge:
        normalized_state = normalize_state(active_challenge['state'])
        if normalized_state != active_challenge['state']:
            update_challenge_admin(thread_id=active_challenge['thread_id'], state=normalized_state)
            active_challenge['state'] = normalized_state
    
    # 상태 선택 옵션
    state_options = [
        ('EGG', STATE_KOREAN[BotStates.EGG]),
        ('DUCKLING', STATE_KOREAN[BotStates.DUCKLING]),
        ('ADOLESCENT', STATE_KOREAN[BotStates.ADOLESCENT]),
        ('ADULT', STATE_KOREAN[BotStates.ADULT]),
        ('SULKY', STATE_KOREAN[BotStates.SULKY]),
        ('RUNAWAY', STATE_KOREAN[BotStates.RUNAWAY]),
        ('DONE', STATE_KOREAN[BotStates.DONE]),
    ]
    
    return render_template('edit_user.html',
                         user=user,
                         challenge=active_challenge,
                         state_options=state_options,
                         state_korean=STATE_KOREAN)

@app.route('/api/users/<bigint:user_id>', methods=['GET'])
@login_required
def api_get_user(user_id):
    """API: 유저 정보 조회 (모달용)"""
    try:
        logger.info(f"[API] 유저 조회 요청: user_id={user_id}")

        # 유저 기본 정보 조회
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_row = c.fetchone()
            if not user_row:
                logger.error(f"[API] 유저를 찾을 수 없음: user_id={user_id}")
                # 모든 user_id 목록 로깅 (디버깅용)
                c.execute("SELECT user_id FROM users ORDER BY user_id")
                all_user_ids = [row['user_id'] for row in c.fetchall()]
                logger.info(f"[API] 데이터베이스 user_id 목록: {all_user_ids}")
                return jsonify({'success': False, 'message': '유저를 찾을 수 없습니다.'}), 404
            user = dict(user_row)

        # 활성 도전 조회
        challenges = get_user_challenges(user_id)
        active_challenge = challenges[0] if challenges else None
        if active_challenge:
            normalized_state = normalize_state(active_challenge['state'])
            if normalized_state != active_challenge['state']:
                update_challenge_admin(thread_id=active_challenge['thread_id'], state=normalized_state)
                active_challenge['state'] = normalized_state

        # 상태 선택 옵션
        state_options = [
            {'value': 'EGG', 'label': STATE_KOREAN[BotStates.EGG]},
            {'value': 'DUCKLING', 'label': STATE_KOREAN[BotStates.DUCKLING]},
            {'value': 'ADOLESCENT', 'label': STATE_KOREAN[BotStates.ADOLESCENT]},
            {'value': 'ADULT', 'label': STATE_KOREAN[BotStates.ADULT]},
            {'value': 'SULKY', 'label': STATE_KOREAN[BotStates.SULKY]},
            {'value': 'RUNAWAY', 'label': STATE_KOREAN[BotStates.RUNAWAY]},
            {'value': 'DONE', 'label': STATE_KOREAN[BotStates.DONE]},
        ]

        return jsonify({
            'success': True,
            'user': {
                # JS Number 정밀도 이슈 방지: Discord snowflake는 문자열로 전달
                'user_id': str(user['user_id']),
                'username': user['username'],
                'gold': user['gold'],
                'ducks_raised': user['ducks_raised']
            },
            'challenge': {
                # JS Number 정밀도 이슈 방지
                'thread_id': str(active_challenge['thread_id']),
                'state': active_challenge['state'],
                'streak': active_challenge['streak'],
                'growth_days': active_challenge['growth_days'],
                'total_days': active_challenge['total_days'],
                'goal_text': active_challenge['goal_text']
            } if active_challenge else None,
            'state_options': state_options
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/users/<bigint:user_id>/update', methods=['POST'])
@login_required
def api_update_user(user_id):
    """API: 유저 정보 업데이트 (모달용)"""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({'success': False, 'message': '요청 본문(JSON)이 올바르지 않습니다.'}), 400
        logger.info(f"[API] 유저 업데이트 요청: user_id={user_id}")
        logger.info(f"[API] 업데이트 데이터: {data}")

        # 유저 기본 정보 업데이트
        gold = int(data.get('gold', 0))
        ducks_raised = int(data.get('ducks_raised', 0))

        # 음수 검증
        if gold < 0 or ducks_raised < 0:
            return jsonify({
                'success': False,
                'message': '골드와 졸업 오리는 0 이상이어야 합니다.'
            }), 400

        with get_db_connection() as conn:
            c = conn.cursor()
            # 유저 존재 확인 로깅
            c.execute("SELECT COUNT(*) as cnt FROM users WHERE user_id = ?", (user_id,))
            if c.fetchone()['cnt'] == 0:
                logger.error(f"[API] 업데이트 실패: user_id={user_id} 없음")
                return jsonify({'success': False, 'message': '유저를 찾을 수 없습니다.'}), 404

            c.execute('''
                UPDATE users
                SET gold = ?, ducks_raised = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (gold, ducks_raised, user_id))

        # 도전 정보 업데이트 (있는 경우)
        challenge_id = data.get('challenge_id')
        if challenge_id:
            state = data.get('state')

            # 상태 값 검증
            if state not in VALID_STATES:
                return jsonify({
                    'success': False,
                    'message': f'유효하지 않은 상태값: {state}'
                }), 400

            streak = int(data.get('streak', 0))
            growth_days = int(data.get('growth_days', 0))
            total_days = int(data.get('total_days', 0))

            # 음수 검증
            if streak < 0 or growth_days < 0 or total_days < 0:
                return jsonify({
                    'success': False,
                    'message': '연속 일수, 성장일, 총 일수는 0 이상이어야 합니다.'
                }), 400

            success = update_challenge_admin(
                thread_id=int(challenge_id),
                state=state,
                streak=streak,
                growth_days=growth_days,
                total_days=total_days
            )

            if not success:
                return jsonify({
                    'success': False,
                    'message': '도전 정보 업데이트에 실패했습니다.'
                }), 500

        # 업데이트된 유저 정보 조회
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            updated_user = dict(c.fetchone())

        return jsonify({
            'success': True,
            'message': '유저 정보가 업데이트되었습니다.',
            'updated_user': {
                # JS Number 정밀도 이슈 방지
                'user_id': str(updated_user['user_id']),
                'username': updated_user['username'],
                'gold': updated_user['gold'],
                'ducks_raised': updated_user['ducks_raised']
            }
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': '잘못된 입력 값입니다.'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/debug/integrity')
@login_required
def debug_integrity():
    """데이터베이스 무결성 검증 페이지"""
    from database import verify_database_integrity

    result = verify_database_integrity()

    return render_template('debug_integrity.html',
                         integrity=result,
                         is_valid=result['is_valid'])


if __name__ == '__main__':
    from config import FLASK_HOST, FLASK_PORT
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
