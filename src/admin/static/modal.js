// 유저 목록 인라인 편집 + 컬럼 정렬
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const table = document.querySelector('.user-table');
        if (!table) {
            return;
        }

        const tbody = table.querySelector('tbody');
        if (!tbody) {
            return;
        }

        let currentEditingCell = null;
        let originalValue = null;

        function getFieldCell(row, field) {
            return row.querySelector(`.editable-cell[data-field="${field}"]`);
        }

        function getFieldValue(row, field) {
            const cell = getFieldCell(row, field);
            if (!cell) {
                return 0;
            }
            const parsed = parseInt(cell.getAttribute('data-value') || '0', 10);
            return Number.isInteger(parsed) ? parsed : 0;
        }

        function getRequestData(row, overrides = {}) {
            const data = {
                gold: getFieldValue(row, 'gold'),
                ducks_raised: getFieldValue(row, 'ducks_raised'),
            };

            const challengeId = row.getAttribute('data-challenge-id');
            if (challengeId) {
                const stateSelect = row.querySelector('.state-select');
                data.challenge_id = challengeId;
                data.state = stateSelect ? stateSelect.value : 'EGG';
                data.streak = getFieldValue(row, 'streak');
                data.growth_days = getFieldValue(row, 'growth_days');
                data.total_days = getFieldValue(row, 'total_days');
            }

            return Object.assign(data, overrides);
        }

        async function saveRow(row, payload) {
            const userId = row.getAttribute('data-user-id');
            const response = await fetch(`/api/users/${userId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            let result;
            try {
                result = await response.json();
            } catch (_) {
                result = { success: false, message: '서버 응답을 해석할 수 없습니다.' };
            }
            return result;
        }

        function updateCellDisplay(cell, value) {
            const emoji = cell.getAttribute('data-emoji') || '';
            const suffix = cell.getAttribute('data-suffix') || '';
            const cellContent = cell.querySelector('.cell-content');
            const display = emoji ? `${emoji} ${value}${suffix}` : `${value}${suffix}`;
            if (cellContent) {
                cellContent.textContent = display;
            }
            cell.setAttribute('data-sort-value', String(value));
        }

        function showErrorTooltip(target, message) {
            const existingTooltip = target.querySelector('.error-tooltip');
            if (existingTooltip) {
                existingTooltip.remove();
            }

            const tooltip = document.createElement('div');
            tooltip.className = 'error-tooltip';
            tooltip.textContent = message;
            target.style.position = 'relative';
            target.appendChild(tooltip);

            setTimeout(() => {
                tooltip.remove();
            }, 3000);
        }

        function enterEditMode(cell) {
            if (cell.classList.contains('saving')) {
                return;
            }

            if (currentEditingCell && currentEditingCell !== cell) {
                exitEditMode(currentEditingCell, true);
            }

            currentEditingCell = cell;
            originalValue = cell.getAttribute('data-value') || '0';

            cell.classList.add('editing');
            const row = cell.closest('tr');
            if (row) {
                row.classList.add('editing-row');
            }

            const input = document.createElement('input');
            input.type = 'number';
            input.className = 'inline-input';
            input.value = originalValue;
            input.min = '0';
            input.step = '1';

            input.addEventListener('keydown', handleKeyDown);
            input.addEventListener('blur', function () {
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

        function exitEditMode(cell, shouldSave) {
            if (!cell || !cell.classList.contains('editing')) {
                return;
            }

            const input = cell.querySelector('.inline-input');
            const newValue = input ? input.value : originalValue;

            if (input) {
                input.remove();
            }

            cell.classList.remove('editing');
            const row = cell.closest('tr');
            if (row) {
                row.classList.remove('editing-row');
            }

            if (shouldSave && newValue !== originalValue) {
                saveNumericValue(cell, newValue);
            } else {
                updateCellDisplay(cell, originalValue);
            }

            currentEditingCell = null;
            originalValue = null;
        }

        function handleKeyDown(event) {
            const input = event.target;
            const cell = input.closest('.editable-cell');
            if (!cell) {
                return;
            }

            if (event.key === 'Enter') {
                event.preventDefault();
                exitEditMode(cell, true);
                moveToNextCell(cell, 'down');
                return;
            }

            if (event.key === 'Tab') {
                event.preventDefault();
                exitEditMode(cell, true);
                moveToNextCell(cell, event.shiftKey ? 'prev' : 'next');
                return;
            }

            if (event.key === 'Escape') {
                event.preventDefault();
                exitEditMode(cell, false);
            }
        }

        function moveToNextCell(currentCell, direction) {
            const row = currentCell.closest('tr');
            if (!row) {
                return;
            }

            const editableCells = Array.from(row.querySelectorAll('.editable-cell'));
            const currentIndex = editableCells.indexOf(currentCell);
            let nextCell = null;

            if (direction === 'next') {
                if (currentIndex < editableCells.length - 1) {
                    nextCell = editableCells[currentIndex + 1];
                } else {
                    const nextRow = row.nextElementSibling;
                    if (nextRow) {
                        nextCell = nextRow.querySelector('.editable-cell');
                    }
                }
            } else if (direction === 'prev') {
                if (currentIndex > 0) {
                    nextCell = editableCells[currentIndex - 1];
                } else {
                    const prevRow = row.previousElementSibling;
                    if (prevRow) {
                        const prevCells = prevRow.querySelectorAll('.editable-cell');
                        nextCell = prevCells[prevCells.length - 1] || null;
                    }
                }
            } else if (direction === 'down') {
                const nextRow = row.nextElementSibling;
                if (nextRow) {
                    const nextCells = Array.from(nextRow.querySelectorAll('.editable-cell'));
                    if (currentIndex < nextCells.length) {
                        nextCell = nextCells[currentIndex];
                    }
                }
            }

            if (nextCell) {
                setTimeout(() => {
                    enterEditMode(nextCell);
                }, 50);
            }
        }

        async function saveNumericValue(cell, rawValue) {
            const parsed = parseInt(rawValue, 10);
            if (!Number.isInteger(parsed) || parsed < 0) {
                cell.classList.add('error');
                showErrorTooltip(cell, '0 이상의 정수만 입력 가능합니다.');
                updateCellDisplay(cell, originalValue || cell.getAttribute('data-value') || '0');
                setTimeout(() => {
                    cell.classList.remove('error');
                }, 1200);
                return;
            }

            const row = cell.closest('tr');
            if (!row) {
                return;
            }

            const field = cell.getAttribute('data-field');
            if (!field) {
                return;
            }

            cell.classList.add('saving');
            const requestData = getRequestData(row, { [field]: parsed });

            try {
                const result = await saveRow(row, requestData);
                cell.classList.remove('saving');

                if (!result.success) {
                    cell.classList.add('error');
                    showErrorTooltip(cell, result.message || '저장에 실패했습니다.');
                    updateCellDisplay(cell, cell.getAttribute('data-value') || '0');
                    setTimeout(() => {
                        cell.classList.remove('error');
                    }, 1600);
                    return;
                }

                cell.setAttribute('data-value', String(parsed));
                updateCellDisplay(cell, parsed);
                cell.classList.add('success');
                setTimeout(() => {
                    cell.classList.remove('success');
                }, 800);
            } catch (error) {
                console.error('저장 오류:', error);
                cell.classList.remove('saving');
                cell.classList.add('error');
                showErrorTooltip(cell, '네트워크 오류가 발생했습니다.');
                updateCellDisplay(cell, cell.getAttribute('data-value') || '0');
                setTimeout(() => {
                    cell.classList.remove('error');
                }, 1600);
            }
        }

        async function handleStateChange(select) {
            const row = select.closest('tr');
            if (!row) {
                return;
            }

            const challengeId = row.getAttribute('data-challenge-id');
            if (!challengeId) {
                return;
            }

            const stateCell = select.closest('.state-cell');
            const prevValue = select.getAttribute('data-prev-value') || select.value;

            select.disabled = true;
            if (stateCell) {
                stateCell.classList.add('saving');
            }

            try {
                const result = await saveRow(row, getRequestData(row, { state: select.value }));

                if (!result.success) {
                    select.value = prevValue;
                    if (stateCell) {
                        stateCell.classList.add('error');
                        showErrorTooltip(stateCell, result.message || '상태 저장에 실패했습니다.');
                        setTimeout(() => {
                            stateCell.classList.remove('error');
                        }, 1600);
                    }
                    return;
                }

                select.setAttribute('data-prev-value', select.value);
                if (stateCell) {
                    stateCell.setAttribute('data-sort-value', select.value);
                    stateCell.classList.add('success');
                    setTimeout(() => {
                        stateCell.classList.remove('success');
                    }, 800);
                }
            } catch (error) {
                console.error('상태 저장 오류:', error);
                select.value = prevValue;
                if (stateCell) {
                    stateCell.classList.add('error');
                    showErrorTooltip(stateCell, '네트워크 오류가 발생했습니다.');
                    setTimeout(() => {
                        stateCell.classList.remove('error');
                    }, 1600);
                }
            } finally {
                if (stateCell) {
                    stateCell.classList.remove('saving');
                }
                select.disabled = false;
            }
        }

        function parseSortValue(row, key, type) {
            const cell = row.querySelector(`[data-key="${key}"]`);
            if (!cell) {
                return type === 'number' || type === 'date' ? Number.NEGATIVE_INFINITY : '';
            }

            const raw = (cell.getAttribute('data-sort-value') || '').trim();

            if (type === 'number') {
                const value = Number(raw);
                return Number.isFinite(value) ? value : Number.NEGATIVE_INFINITY;
            }

            if (type === 'date') {
                if (!raw) {
                    return Number.NEGATIVE_INFINITY;
                }
                const timestamp = Date.parse(raw);
                return Number.isFinite(timestamp) ? timestamp : Number.NEGATIVE_INFINITY;
            }

            return raw.toLowerCase();
        }

        function applySortIndicator(activeHeader, direction) {
            const headers = table.querySelectorAll('th.sortable');
            headers.forEach((header) => {
                header.classList.remove('sort-asc', 'sort-desc');
            });

            if (activeHeader) {
                activeHeader.classList.add(direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        }

        function sortRows(key, type, direction) {
            const rows = Array.from(tbody.querySelectorAll('tr[data-user-id]'));
            rows.sort((a, b) => {
                const aValue = parseSortValue(a, key, type);
                const bValue = parseSortValue(b, key, type);

                if (aValue < bValue) {
                    return -1;
                }
                if (aValue > bValue) {
                    return 1;
                }
                return 0;
            });

            if (direction === 'desc') {
                rows.reverse();
            }

            rows.forEach((row) => {
                tbody.appendChild(row);
            });
        }

        function attachInlineEditors() {
            const editableCells = table.querySelectorAll('.editable-cell');
            editableCells.forEach((cell) => {
                cell.addEventListener('dblclick', function () {
                    enterEditMode(this);
                });
            });
        }

        function attachStateEditors() {
            const stateSelects = table.querySelectorAll('.state-select');
            stateSelects.forEach((select) => {
                select.addEventListener('change', function () {
                    handleStateChange(this);
                });
            });
        }

        function attachSortHandlers() {
            let currentKey = '';
            let currentDirection = 'asc';

            const headers = table.querySelectorAll('th.sortable');
            headers.forEach((header) => {
                header.addEventListener('click', function () {
                    const key = this.getAttribute('data-key');
                    const type = this.getAttribute('data-type') || 'text';
                    if (!key) {
                        return;
                    }

                    if (currentKey === key) {
                        currentDirection = currentDirection === 'asc' ? 'desc' : 'asc';
                    } else {
                        currentKey = key;
                        currentDirection = 'asc';
                    }

                    sortRows(currentKey, type, currentDirection);
                    applySortIndicator(this, currentDirection);
                });
            });
        }

        attachInlineEditors();
        attachStateEditors();
        attachSortHandlers();
    });
})();
