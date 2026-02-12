// 모달 인라인 편집 기능
(function() {
    'use strict';

    const modal = document.getElementById('edit-modal');
    const modalContent = document.getElementById('modal-body');
    const closeBtn = document.querySelector('.modal-close');
    let currentUserId = null; // string: 64비트 user_id를 문자열로 처리

    // 모달 열기
    async function openModal(userId) {
        currentUserId = userId;
        modal.classList.add('active');
        showLoading();

        try {
            const response = await fetch(`/api/users/${userId}`);
            const data = await response.json();

            if (!data.success) {
                const errorMsg = data.message || '유저 정보를 불러올 수 없습니다.';
                console.error('[Modal] API 오류:', errorMsg, '(user_id:', userId, ')');
                showError(`${errorMsg} (user_id: ${userId})`);
                return;
            }

            renderForm(data);
        } catch (error) {
            showError('유저 정보를 불러오는 중 오류가 발생했습니다.');
            console.error('Error:', error);
        }
    }

    // 모달 닫기
    function closeModal() {
        modal.classList.remove('active');
        currentUserId = null;
        modalContent.innerHTML = '';
    }

    // 로딩 표시
    function showLoading() {
        modalContent.innerHTML = '<div class="modal-loading">데이터를 불러오는 중...</div>';
    }

    // 에러 표시
    function showError(message) {
        modalContent.innerHTML = `<div class="modal-error">${message}</div>`;
    }

    // 성공 메시지 표시
    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'modal-success';
        successDiv.textContent = message;
        modalContent.insertBefore(successDiv, modalContent.firstChild);

        setTimeout(() => {
            successDiv.remove();
        }, 3000);
    }

    // 폼 렌더링
    function renderForm(data) {
        const { user, challenge, state_options } = data;

        let formHTML = `
            <form id="edit-form">
                <div class="form-group">
                    <label>유저 ID</label>
                    <input type="text" value="${user.user_id}" disabled>
                </div>

                <div class="form-group">
                    <label>유저명</label>
                    <input type="text" value="${user.username || '(없음)'}" disabled>
                </div>

                <div class="form-group">
                    <label for="gold">골드 💰</label>
                    <input type="number" id="gold" name="gold" value="${user.gold}" min="0" required>
                </div>

                <div class="form-group">
                    <label for="ducks_raised">졸업 오리 🎓</label>
                    <input type="number" id="ducks_raised" name="ducks_raised" value="${user.ducks_raised}" min="0" required>
                </div>

                <div class="challenge-section">
                    <h4>🦆 활성 도전</h4>
        `;

        if (challenge) {
            formHTML += `
                <input type="hidden" id="challenge_id" value="${challenge.thread_id}">

                <div class="form-group">
                    <label>목표</label>
                    <input type="text" value="${challenge.goal_text}" disabled>
                </div>

                <div class="form-group">
                    <label for="state">오리 상태</label>
                    <select id="state" name="state" required>
                        ${state_options.map(opt => `
                            <option value="${opt.value}" ${opt.value === challenge.state ? 'selected' : ''}>
                                ${opt.label}
                            </option>
                        `).join('')}
                    </select>
                </div>

                <div class="form-group">
                    <label for="streak">연속 일수 🔥</label>
                    <input type="number" id="streak" name="streak" value="${challenge.streak}" min="0" required>
                </div>

                <div class="form-group">
                    <label for="total_days">총 일수 📅</label>
                    <input type="number" id="total_days" name="total_days" value="${challenge.total_days}" min="0" required>
                </div>
            `;
        } else {
            formHTML += '<div class="no-challenge">활성화된 도전이 없습니다.</div>';
        }

        formHTML += `
                </div>

                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">저장</button>
                    <button type="button" class="btn btn-secondary" id="cancel-btn">취소</button>
                </div>
            </form>
        `;

        modalContent.innerHTML = formHTML;

        // 이벤트 리스너 등록
        document.getElementById('edit-form').addEventListener('submit', handleSubmit);
        document.getElementById('cancel-btn').addEventListener('click', closeModal);
    }

    // 폼 제출 처리
    async function handleSubmit(event) {
        event.preventDefault();

        const submitBtn = event.target.querySelector('button[type="submit"]');
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;

        const formData = {
            gold: parseInt(document.getElementById('gold').value),
            ducks_raised: parseInt(document.getElementById('ducks_raised').value)
        };

        // 도전 정보가 있는 경우
        const challengeIdInput = document.getElementById('challenge_id');
        if (challengeIdInput) {
            formData.challenge_id = challengeIdInput.value;
            formData.state = document.getElementById('state').value;
            formData.streak = parseInt(document.getElementById('streak').value);
            formData.total_days = parseInt(document.getElementById('total_days').value);
        }

        try {
            const response = await fetch(`/api/users/${currentUserId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (!result.success) {
                showError(result.message);
                submitBtn.classList.remove('loading');
                submitBtn.disabled = false;
                return;
            }

            // 테이블 행 업데이트
            updateTableRow(result.updated_user);

            // 성공 메시지 표시 후 모달 닫기
            showSuccess(result.message);
            setTimeout(() => {
                closeModal();
            }, 1000);

        } catch (error) {
            showError('저장 중 오류가 발생했습니다.');
            console.error('Error:', error);
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        }
    }

    // 테이블 행 실시간 업데이트
    function updateTableRow(userData) {
        const rows = document.querySelectorAll('.user-table tbody tr');

        rows.forEach(row => {
            const userIdCell = row.querySelector('td:first-child');
            if (userIdCell && userIdCell.textContent === String(userData.user_id)) {
                // 골드 업데이트
                const goldCell = row.querySelector('td:nth-child(4)');
                if (goldCell) {
                    goldCell.textContent = `💰 ${userData.gold}G`;
                }

                // 졸업 오리 업데이트
                const ducksCell = row.querySelector('td:nth-child(3)');
                if (ducksCell) {
                    ducksCell.textContent = `🎓 ${userData.ducks_raised}`;
                }
            }
        });
    }

    // 이벤트 리스너 등록
    document.addEventListener('DOMContentLoaded', function() {
        // 모든 수정 버튼에 이벤트 리스너 추가
        const editButtons = document.querySelectorAll('.btn-edit');
        editButtons.forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.getAttribute('data-user-id'); // 문자열로 유지
                openModal(userId);
            });
        });

        // 닫기 버튼
        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }

        // 모달 외부 클릭 시 닫기
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeModal();
            }
        });

        // ESC 키로 닫기
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && modal.classList.contains('active')) {
                closeModal();
            }
        });
    });
})();
