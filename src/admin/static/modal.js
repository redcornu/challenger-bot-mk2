// 모달 및 인라인 편집 기능
(function() {
    'use strict';

    const modal = document.getElementById('edit-modal');
    const modalContent = document.getElementById('modal-body');
    const closeBtn = document.querySelector('.modal-close');
    let currentUserId = null; // string: 64비트 user_id를 문자열로 처리

    // ==================== 인라인 편집 상태 관리 ====================
    let currentEditingCell = null;
    let originalValue = null;

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

    // ==================== 인라인 편집 함수들 ====================

    // 편집 모드 진입
    function enterEditMode(cell) {
        // 이미 편집 중인 셀이 있으면 저장하고 종료
        if (currentEditingCell && currentEditingCell !== cell) {
            exitEditMode(currentEditingCell, true);
        }

        currentEditingCell = cell;
        originalValue = cell.getAttribute('data-value');

        // 셀 스타일 변경
        cell.classList.add('editing');
        const row = cell.closest('tr');
        row.classList.add('editing-row');

        // input 생성
        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'inline-input';
        input.value = originalValue;
        input.min = '0';
        input.step = '1';

        // 이벤트 리스너
        input.addEventListener('keydown', handleKeyDown);
        input.addEventListener('blur', function() {
            // blur 시 값이 변경되었으면 저장
            if (input.value !== originalValue) {
                exitEditMode(cell, true);
            } else {
                exitEditMode(cell, false);
            }
        });

        cell.appendChild(input);
        input.focus();
        input.select();
    }

    // 편집 모드 종료
    function exitEditMode(cell, shouldSave) {
        if (!cell || !cell.classList.contains('editing')) {
            return;
        }

        const input = cell.querySelector('.inline-input');
        const newValue = input ? input.value : originalValue;

        // input 제거
        if (input) {
            input.remove();
        }

        // 스타일 복원
        cell.classList.remove('editing');
        const row = cell.closest('tr');
        row.classList.remove('editing-row');

        if (shouldSave && newValue !== originalValue) {
            saveValue(cell, newValue);
        } else {
            // 저장하지 않으면 원래 값으로 복원
            updateCellDisplay(cell, originalValue);
        }

        currentEditingCell = null;
        originalValue = null;
    }

    // 키보드 이벤트 처리
    function handleKeyDown(event) {
        const input = event.target;
        const cell = input.closest('.editable-cell');

        switch(event.key) {
            case 'Enter':
                event.preventDefault();
                exitEditMode(cell, true);
                // 다음 행의 같은 컬럼으로 이동
                moveToNextCell(cell, 'down');
                break;
            case 'Tab':
                event.preventDefault();
                exitEditMode(cell, true);
                // Tab: 다음 셀, Shift+Tab: 이전 셀
                moveToNextCell(cell, event.shiftKey ? 'prev' : 'next');
                break;
            case 'Escape':
                event.preventDefault();
                exitEditMode(cell, false);
                break;
        }
    }

    // 다음 셀로 이동
    function moveToNextCell(currentCell, direction) {
        const row = currentCell.closest('tr');
        const cells = Array.from(row.querySelectorAll('.editable-cell'));
        const currentIndex = cells.indexOf(currentCell);

        let nextCell = null;

        if (direction === 'next') {
            // 같은 행의 다음 편집 가능 셀
            if (currentIndex < cells.length - 1) {
                nextCell = cells[currentIndex + 1];
            } else {
                // 다음 행의 첫 번째 편집 가능 셀
                const nextRow = row.nextElementSibling;
                if (nextRow) {
                    nextCell = nextRow.querySelector('.editable-cell');
                }
            }
        } else if (direction === 'prev') {
            // 같은 행의 이전 편집 가능 셀
            if (currentIndex > 0) {
                nextCell = cells[currentIndex - 1];
            } else {
                // 이전 행의 마지막 편집 가능 셀
                const prevRow = row.previousElementSibling;
                if (prevRow) {
                    const prevCells = prevRow.querySelectorAll('.editable-cell');
                    nextCell = prevCells[prevCells.length - 1];
                }
            }
        } else if (direction === 'down') {
            // 다음 행의 같은 컬럼
            const nextRow = row.nextElementSibling;
            if (nextRow) {
                const nextCells = Array.from(nextRow.querySelectorAll('.editable-cell'));
                if (currentIndex < nextCells.length) {
                    nextCell = nextCells[currentIndex];
                }
            }
        }

        if (nextCell) {
            // 약간의 지연 후 다음 셀 편집
            setTimeout(() => {
                enterEditMode(nextCell);
            }, 50);
        }
    }

    // API 호출 및 저장
    async function saveValue(cell, newValue) {
        const row = cell.closest('tr');
        const userId = row.getAttribute('data-user-id');
        const field = cell.getAttribute('data-field');

        // 저장 중 표시
        cell.classList.add('saving');

        // 현재 행의 모든 데이터 수집
        const requestData = {};
        const editableCells = row.querySelectorAll('.editable-cell');
        editableCells.forEach(c => {
            const f = c.getAttribute('data-field');
            if (c === cell) {
                requestData[f] = parseInt(newValue);
            } else {
                requestData[f] = parseInt(c.getAttribute('data-value'));
            }
        });

        try {
            const response = await fetch(`/api/users/${userId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            // 저장 중 표시 제거
            cell.classList.remove('saving');

            if (!result.success) {
                // 에러 처리
                cell.classList.add('error');
                showErrorTooltip(cell, result.message || '저장에 실패했습니다.');

                // 원래 값으로 복원
                setTimeout(() => {
                    cell.classList.remove('error');
                    updateCellDisplay(cell, originalValue);
                }, 3000);

                return;
            }

            // 성공 처리
            cell.classList.add('success');

            // data-value 업데이트
            cell.setAttribute('data-value', newValue);
            updateCellDisplay(cell, newValue);

            // 성공 애니메이션 제거
            setTimeout(() => {
                cell.classList.remove('success');
            }, 800);

        } catch (error) {
            console.error('저장 오류:', error);

            // 저장 중 표시 제거
            cell.classList.remove('saving');

            // 에러 처리
            cell.classList.add('error');
            showErrorTooltip(cell, '네트워크 오류가 발생했습니다.');

            // 원래 값으로 복원
            setTimeout(() => {
                cell.classList.remove('error');
                updateCellDisplay(cell, originalValue);
            }, 3000);
        }
    }

    // 셀 표시 업데이트
    function updateCellDisplay(cell, value) {
        const emoji = cell.getAttribute('data-emoji') || '';
        const suffix = cell.getAttribute('data-suffix') || '';
        const cellContent = cell.querySelector('.cell-content');

        if (cellContent) {
            cellContent.textContent = `${emoji} ${value}${suffix}`;
        }
    }

    // 에러 툴팁 표시
    function showErrorTooltip(cell, message) {
        // 기존 툴팁 제거
        const existingTooltip = cell.querySelector('.error-tooltip');
        if (existingTooltip) {
            existingTooltip.remove();
        }

        // 새 툴팁 생성
        const tooltip = document.createElement('div');
        tooltip.className = 'error-tooltip';
        tooltip.textContent = message;
        cell.style.position = 'relative';
        cell.appendChild(tooltip);

        // 3초 후 제거
        setTimeout(() => {
            tooltip.remove();
        }, 3000);
    }

    // 편집 리스너 등록
    function attachEditListeners() {
        const editableCells = document.querySelectorAll('.editable-cell');
        editableCells.forEach(cell => {
            // 더블클릭으로 편집 시작
            cell.addEventListener('dblclick', function() {
                enterEditMode(this);
            });
        });
    }

    // ==================== 이벤트 리스너 등록 ====================
    document.addEventListener('DOMContentLoaded', function() {
        // 인라인 편집 리스너 등록
        attachEditListeners();

        // 모든 고급 설정 버튼에 이벤트 리스너 추가
        const advancedButtons = document.querySelectorAll('.btn-advanced');
        advancedButtons.forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.getAttribute('data-user-id'); // 문자열로 유지
                openModal(userId);
            });
        });

        // 모달 닫기 버튼
        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }

        // 모달 외부 클릭 시 닫기
        if (modal) {
            modal.addEventListener('click', function(event) {
                if (event.target === modal) {
                    closeModal();
                }
            });
        }

        // ESC 키로 모달 닫기 (인라인 편집 중이 아닐 때만)
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && modal.classList.contains('active') && !currentEditingCell) {
                closeModal();
            }
        });
    });
})();
