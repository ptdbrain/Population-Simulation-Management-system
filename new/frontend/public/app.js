// ==========================================
// VIETNAMESE ADMIN DASHBOARD - COMPLETE APP
// ==========================================

// ==========================================
// GLOBAL STATE
// ==========================================
const State = {
    user: null,
    token: null,
    currentTab: 'statistics',
    households: [],
    persons: [],
    absentRequests: [],
    tempResidences: [],
    complaints: [],
    isLoading: false
};

// API Base URL
const API_BASE = '/api';

// ==========================================
// UTILITIES
// ==========================================

// Parse JWT token
function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

// Format date
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

// ==========================================
// API UTILITIES
// ==========================================

async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('token');

    // Prepend API_BASE if not already
    let url = endpoint.startsWith('/api') ? endpoint : API_BASE + endpoint;

    // Add trailing slash if endpoint is a collection route (no path params after)
    // This fixes FastAPI 404 issues for routes like /households vs /households/
    // Note: absent-requests and temp-residences don't have trailing slash in backend
    const collectionRoutes = ['/households', '/persons', '/complaints'];
    for (const route of collectionRoutes) {
        if (url.endsWith(route)) {
            url += '/';
            break;
        }
    }

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        }
    };

    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, finalOptions);

        // Handle 401 Unauthorized
        if (response.status === 401) {
            logout();
            showToast('Phiên đăng nhập đã hết hạn', 'error');
            return null;
        }

        // Handle other errors
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Lỗi không xác định' }));
            throw new Error(error.detail || 'Có lỗi xảy ra');
        }

        return await response.json();
    } catch (error) {
        showToast(error.message, 'error');
        throw error;
    }
}

// ==========================================
// AUTHENTICATION
// ==========================================

function showLoginModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'login-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Đăng nhập hệ thống</h3>
            </div>
            <div class="modal-body">
                <form id="login-form" onsubmit="handleLogin(event)">
                    <div class="form-group">
                        <label for="login-username">Tên đăng nhập</label>
                        <input type="text" id="login-username" name="username" required autofocus>
                    </div>
                    <div class="form-group">
                        <label for="login-password">Mật khẩu</label>
                        <input type="password" id="login-password" name="password" required>
                    </div>
                    <div class="text-muted mb-2">
                        <strong>Tài khoản test:</strong><br>
                        admin / admin123<br>
                        leader / leader123<br>
                        resident1 / res123
                    </div>
                    <button type="submit" class="btn-add" style="width: 100%; margin-top: 16px;">
                        Đăng nhập
                    </button>
                </form>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    document.getElementById('login-username').focus();
}

async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
        showLoading();

        const response = await fetch('/api/token', {
            method: 'POST',
            body: formData,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        if (!response.ok) {
            throw new Error('Sai tên đăng nhập hoặc mật khẩu');
        }

        const data = await response.json();

        // Save token
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', username);

        // Parse token to get user info
        const payload = parseJwt(data.access_token);
        State.token = data.access_token;
        State.user = { username, ...payload };

        // Close modal and show dashboard
        closeModal('login-modal');
        showDashboard();
        showToast('Đăng nhập thành công!', 'success');

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    State.user = null;
    State.token = null;

    // Show login overlay, hide main content
    document.getElementById('auth-overlay').style.display = 'flex';
    document.querySelector('.sidebar').style.display = 'none';
    document.querySelector('.main-wrapper').style.display = 'none';
}

function checkAuth() {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');

    if (!token) {
        // Show the HTML auth-overlay instead of creating a modal
        const authOverlay = document.getElementById('auth-overlay');
        if (authOverlay) {
            authOverlay.style.display = 'flex';
        }
        document.querySelector('.sidebar').style.display = 'none';
        document.querySelector('.main-wrapper').style.display = 'none';
        return false;
    }

    // Validate token
    const payload = parseJwt(token);
    if (!payload) {
        const authOverlay = document.getElementById('auth-overlay');
        if (authOverlay) {
            authOverlay.style.display = 'flex';
        }
        document.querySelector('.sidebar').style.display = 'none';
        document.querySelector('.main-wrapper').style.display = 'none';
        return false;
    }

    // Check if expired
    if (payload.exp && payload.exp * 1000 < Date.now()) {
        logout();
        showToast('Phiên đăng nhập đã hết hạn', 'error');
        return false;
    }

    State.token = token;
    State.user = { username, ...payload };
    return true;
}

function showDashboard() {
    // Hide login overlay
    document.getElementById('auth-overlay').style.display = 'none';

    // Show main dashboard
    document.querySelector('.sidebar').style.display = 'flex';
    document.querySelector('.main-wrapper').style.display = 'flex';

    // Update user info in sidebar
    updateUserDisplay();

    // Load initial data (statistics tab is default)
    switchTab('statistics');
}

function updateUserDisplay() {
    // Update sidebar user info
    if (State.user) {
        const nameEl = document.getElementById('user-display-name');
        if (nameEl) nameEl.textContent = State.user.username;
        // Verify role mapping if needed
    }
}

// ==========================================
// TAB SWITCHING
// ==========================================

// ==========================================
// TAB SWITCHING
// ==========================================

function switchTab(tabName) {
    // Remove active class from all sidebar items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        // Simple check if this item corresponds to the clicked tab
        if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(`'${tabName}'`)) {
            item.classList.add('active');
        }
    });

    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Show corresponding content
    const content = document.getElementById('tab-' + tabName);
    if (content) {
        content.classList.add('active');
        State.currentTab = tabName;

        // Update Page Title
        const requestTitle = {
            'statistics': 'Tổng quan Tổ dân phố',
            'households': 'Quản lý Hộ khẩu',
            'persons': 'Quản lý Nhân khẩu',
            'temporary': 'Quản lý Tạm trú / Tạm vắng',
            'complaints': 'Phản ánh & Kiến nghị'
        };
        document.getElementById('page-title').textContent = requestTitle[tabName] || 'Dashboard';
    }

    // Load data for the tab
    if (tabName === 'households') {
        loadHouseholds();
    } else if (tabName === 'persons') {
        loadPersons();
    } else if (tabName === 'temporary') {
        loadAbsentRequests();
    } else if (tabName === 'complaints') {
        loadComplaints();
    } else if (tabName === 'statistics') {
        loadStatistics();
    }
}

// ==========================================
// HOUSEHOLDS MANAGEMENT
// ==========================================

async function loadHouseholds() {
    try {
        showLoading();
        const data = await apiCall('/households');

        if (data) {
            State.households = data;
            updatePagination(data.length);
        }
    } catch (error) {
        console.error('Error loading households:', error);
    } finally {
        hideLoading();
    }
}

function renderHouseholdsTable(households) {
    const tbody = document.querySelector('#household-table tbody');

    if (!households || households.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">🏠</div>
                    <p>Chưa có hộ khẩu nào</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = households.map(h => `
        <tr>
            <td><strong>${h.household_code || ''}</strong></td>
            <td>${h.owner_name || 'Chưa có'}</td>
            <td>${h.address || ''}</td>
            <td class="text-center">${h.resident_count || 0}</td>
            <td class="text-right">
                <div class="action-icons">
                    <button class="action-btn" onclick="editHousehold(${h.id})" title="Chỉnh sửa">✏️</button>
                    <button class="action-btn btn-text-delete" onclick="deleteHousehold(${h.id}, '${h.household_code}')" title="Xóa">🗑️</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function searchHouseholds() {
    const searchValue = document.getElementById('search-input').value.toLowerCase();

    if (!searchValue.trim()) {
        // If empty, show all with pagination
        updatePagination(State.households.length);
        return;
    }

    const filtered = State.households.filter(h => {
        const code = (h.household_code || '').toLowerCase();
        const address = (h.address || '').toLowerCase();
        return code.includes(searchValue) || address.includes(searchValue);
    });

    // Show filtered results without pagination
    Pagination.currentPage = 1;
    Pagination.totalItems = filtered.length;
    renderHouseholdsTable(filtered);
    renderPagination();
}

function addHousehold() {
    showModal('Thêm hộ khẩu mới', `
        <form id="add-household-form" onsubmit="handleAddHousehold(event)">
            <div class="form-group">
                <label for="household-code">Số hộ khẩu *</label>
                <input type="text" id="household-code" name="household_code" required>
            </div>
            <div class="form-group">
                <label for="household-address">Địa chỉ *</label>
                <input type="text" id="household-address" name="address" required>
            </div>
            <div class="form-group">
                <label for="owner-id">ID chủ hộ (optional)</label>
                <input type="number" id="owner-id" name="owner_id">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Thêm</button>
            </div>
        </form>
    `);
}

async function handleAddHousehold(event) {
    event.preventDefault();

    const formData = {
        household_code: document.getElementById('household-code').value,
        address: document.getElementById('household-address').value,
        owner_id: document.getElementById('owner-id').value || null
    };

    try {
        showLoading();
        const result = await apiCall('/households', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (result) {
            showToast('Đã thêm hộ khẩu mới', 'success');
            closeModal();
            loadHouseholds();
        }
    } catch (error) {
        console.error('Error adding household:', error);
    } finally {
        hideLoading();
    }
}

async function editHousehold(id) {
    // Find household data
    const household = State.households.find(h => h.id === id);
    if (!household) {
        showToast('Không tìm thấy hộ khẩu', 'error');
        return;
    }

    showModal('Chỉnh sửa hộ khẩu', `
        <form id="edit-household-form" onsubmit="handleEditHousehold(event, ${id})">
            <div class="form-group">
                <label for="edit-household-code">Số hộ khẩu *</label>
                <input type="text" id="edit-household-code" name="household_code" value="${household.household_code || ''}" required>
            </div>
            <div class="form-group">
                <label for="edit-household-address">Địa chỉ *</label>
                <input type="text" id="edit-household-address" name="address" value="${household.address || ''}" required>
            </div>
            <div class="form-group">
                <label for="edit-owner-id">ID chủ hộ (optional)</label>
                <input type="number" id="edit-owner-id" name="owner_id" value="${household.owner_id || ''}">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Lưu</button>
            </div>
        </form>
    `);
}

async function handleEditHousehold(event, id) {
    event.preventDefault();

    const formData = {
        household_code: document.getElementById('edit-household-code').value,
        address: document.getElementById('edit-household-address').value,
        owner_id: document.getElementById('edit-owner-id').value || null
    };

    try {
        showLoading();
        const result = await apiCall(`/households/${id}`, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });

        if (result) {
            showToast('Đã cập nhật hộ khẩu', 'success');
            closeModal();
            loadHouseholds();
        }
    } catch (error) {
        console.error('Error editing household:', error);
    } finally {
        hideLoading();
    }
}

async function deleteHousehold(id, code) {
    if (!confirm(`Bạn có chắc chắn muốn xóa hộ khẩu ${code}?`)) {
        return;
    }

    try {
        showLoading();
        await apiCall(`/households/${id}`, { method: 'DELETE' });
        showToast('Đã xóa hộ khẩu', 'success');
        loadHouseholds();
    } catch (error) {
        console.error('Error deleting household:', error);
    } finally {
        hideLoading();
    }
}

// ==========================================
// HOUSEHOLD SPLIT OPERATION
// ==========================================

function showSplitHouseholdForm() {
    showModal('Tách hộ khẩu', `
        <form id="split-household-form" onsubmit="handleSplitHousehold(event)">
            <div class="form-group">
                <label for="split-old-household">ID hộ khẩu cũ *</label>
                <select id="split-old-household" required onchange="updateResidentsList()">
                    <option value="">-- Chọn hộ khẩu --</option>
                    ${State.households.map(h => `
                        <option value="${h.id}">${h.household_code} - ${h.address}</option>
                    `).join('')}
                </select>
            </div>
            
            <div class="form-group">
                <label for="split-new-owner">ID chủ hộ mới *</label>
                <input type="number" id="split-new-owner" name="new_owner_id" required>
                <small class="text-muted">ID của người sẽ làm chủ hộ mới</small>
            </div>
            
            <div class="form-group">
                <label for="split-moving-ids">ID các thành viên chuyển đi *</label>
                <input type="text" id="split-moving-ids" name="moving_resident_ids" required placeholder="VD: 1,2,3">
                <small class="text-muted">Nhập các ID cách nhau bởi dấu phẩy</small>
            </div>
            
            <div class="form-group">
                <label for="split-new-code">Số hộ khẩu mới *</label>
                <input type="text" id="split-new-code" name="new_household_code" required>
            </div>
            
            <div class="form-group">
                <label for="split-new-address">Địa chỉ mới *</label>
                <input type="text" id="split-new-address" name="new_address" required>
            </div>
            
            <div class="form-group">
                <label for="split-replacement-id">ID chủ hộ thay thế (nếu cần)</label>
                <input type="number" id="split-replacement-id" name="replacement_owner_id">
                <small class="text-muted">Chỉ cần nếu chủ hộ cũ chuyển đi</small>
            </div>
            
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Thực hiện tách hộ</button>
            </div>
        </form>
    `);
}

async function handleSplitHousehold(event) {
    event.preventDefault();

    const movingIdsStr = document.getElementById('split-moving-ids').value;
    const movingIds = movingIdsStr.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));

    if (movingIds.length === 0) {
        showToast('Vui lòng nhập ít nhất một ID thành viên', 'error');
        return;
    }

    const formData = {
        old_household_id: parseInt(document.getElementById('split-old-household').value),
        new_owner_id: parseInt(document.getElementById('split-new-owner').value),
        moving_resident_ids: movingIds,
        new_household_code: document.getElementById('split-new-code').value,
        new_address: document.getElementById('split-new-address').value,
        replacement_owner_id: document.getElementById('split-replacement-id').value ?
            parseInt(document.getElementById('split-replacement-id').value) : null
    };

    try {
        showLoading();
        const result = await apiCall('/households/split', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (result) {
            showToast('Tách hộ thành công!', 'success');
            closeModal();
            loadHouseholds();
        }
    } catch (error) {
        console.error('Error splitting household:', error);
    } finally {
        hideLoading();
    }
}

// ==========================================
// PAGINATION
// ==========================================

const Pagination = {
    currentPage: 1,
    itemsPerPage: 10,
    totalItems: 0
};

function renderPagination() {
    const totalPages = Math.ceil(Pagination.totalItems / Pagination.itemsPerPage);

    if (totalPages <= 1) {
        document.getElementById('pagination-container').innerHTML = '';
        return;
    }

    let paginationHTML = '<div class="pagination">';

    // Previous button
    paginationHTML += `
        <button class="pagination-btn" 
                onclick="changePage(${Pagination.currentPage - 1})"
                ${Pagination.currentPage === 1 ? 'disabled' : ''}>
            ‹ Trước
        </button>
    `;

    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= Pagination.currentPage - 1 && i <= Pagination.currentPage + 1)) {
            paginationHTML += `
                <button class="pagination-btn ${i === Pagination.currentPage ? 'active' : ''}"
                        onclick="changePage(${i})">
                    ${i}
                </button>
            `;
        } else if (i === Pagination.currentPage - 2 || i === Pagination.currentPage + 2) {
            paginationHTML += '<span class="pagination-dots">...</span>';
        }
    }

    // Next button
    paginationHTML += `
        <button class="pagination-btn" 
                onclick="changePage(${Pagination.currentPage + 1})"
                ${Pagination.currentPage === totalPages ? 'disabled' : ''}>
            Sau ›
        </button>
    `;

    paginationHTML += '</div>';

    document.getElementById('pagination-container').innerHTML = paginationHTML;
}

function changePage(page) {
    const totalPages = Math.ceil(Pagination.totalItems / Pagination.itemsPerPage);

    if (page < 1 || page > totalPages) return;

    Pagination.currentPage = page;
    renderCurrentPage();
}

function renderCurrentPage() {
    const start = (Pagination.currentPage - 1) * Pagination.itemsPerPage;
    const end = start + Pagination.itemsPerPage;
    const pageData = State.households.slice(start, end);

    renderHouseholdsTable(pageData);
    renderPagination();
}

function updatePagination(totalItems) {
    Pagination.totalItems = totalItems;
    Pagination.currentPage = 1;
    renderCurrentPage();
}

// ==========================================
// PERSONS MANAGEMENT
// ==========================================

const PersonsPagination = {
    currentPage: 1,
    itemsPerPage: 10,
    totalItems: 0
};

async function loadPersons() {
    try {
        showLoading();
        const data = await apiCall('/persons');

        if (data) {
            State.persons = data;
            updatePersonsPagination(data.length);
            populateHouseholdFilter();
        }
    } catch (error) {
        console.error('Error loading persons:', error);
        // Show empty state
        document.querySelector('#persons-table tbody').innerHTML = `
            <tr>
                <td colspan="7" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">❌</div>
                    <p>Không thể tải dữ liệu nhân khẩu</p>
                </td>
            </tr>
        `;
    } finally {
        hideLoading();
    }
}

function renderPersonsTable(persons) {
    const tbody = document.querySelector('#persons-table tbody');

    if (!persons || persons.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">👥</div>
                    <p>Chưa có nhân khẩu nào</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = persons.map(p => {
        const household = State.households.find(h => h.id === p.household_id);
        const householdCode = household ? household.household_code : 'N/A';

        // Status badge
        const statusBadge = {
            'PERMANENT': '<span class="badge badge-success">Thường trú</span>',
            'TEMPORARY': '<span class="badge badge-warning">Tạm trú</span>',
            'ABSENT': '<span class="badge badge-info">Tạm vắng</span>'
        }[p.status] || '<span class="badge badge-neutral">Khác</span>';

        return `
        <tr>
            <td><strong>${p.full_name || ''}</strong></td>
            <td>${p.cid || ''}</td>
            <td>${formatDate(p.dob)}</td>
            <td class="text-center">${p.gender === 'MALE' ? 'Nam' : 'Nữ'}</td>
            <td>${householdCode}</td>
            <td>${statusBadge}</td>
            <td class="text-right">
                <div class="action-icons">
                    <button class="action-btn" onclick="editPerson(${p.id})" title="Chỉnh sửa">✏️</button>
                    <button class="action-btn btn-text-delete" onclick="deletePerson(${p.id}, '${p.full_name}')" title="Xóa">🗑️</button>
                </div>
            </td>
        </tr>
    `}).join('');
}

function populateHouseholdFilter() {
    const select = document.getElementById('household-filter');
    if (!select) return; // Guard against missing element

    const options = State.households.map(h =>
        `<option value="${h.id}">${h.household_code} - ${h.address}</option>`
    ).join('');

    select.innerHTML = `<option value="">-- Tất cả hộ khẩu --</option>${options}`;
}

function filterPersons() {
    const householdFilterEl = document.getElementById('household-filter');
    const searchInputEl = document.getElementById('persons-search-input');

    const householdId = householdFilterEl ? householdFilterEl.value : '';
    const searchValue = searchInputEl ? searchInputEl.value.toLowerCase() : '';

    let filtered = State.persons;

    // Filter by household
    if (householdId) {
        filtered = filtered.filter(p => p.household_id == householdId);
    }

    // Filter by search
    if (searchValue.trim()) {
        filtered = filtered.filter(p => {
            const name = (p.full_name || '').toLowerCase();
            const cid = (p.cid || '').toLowerCase();
            return name.includes(searchValue) || cid.includes(searchValue);
        });
    }

    PersonsPagination.currentPage = 1;
    PersonsPagination.totalItems = filtered.length;

    if (PersonsPagination.itemsPerPage >= filtered.length) {
        renderPersonsTable(filtered);
        const paginationEl = document.getElementById('persons-pagination-container');
        if (paginationEl) paginationEl.innerHTML = '';
    } else {
        const start = 0;
        const end = PersonsPagination.itemsPerPage;
        renderPersonsTable(filtered.slice(start, end));
        renderPersonsPagination(filtered);
    }
}

function searchPersons() {
    filterPersons();
}

function addPerson() {
    showModal('Thêm nhân khẩu mới', `
        <form id="add-person-form" onsubmit="handleAddPerson(event)">
            <div class="form-group">
                <label for="person-name">Họ và tên *</label>
                <input type="text" id="person-name" name="full_name" required>
            </div>
            <div class="form-group">
                <label for="person-dob">Ngày sinh *</label>
                <input type="date" id="person-dob" name="dob" required>
            </div>
            <div class="form-group">
                <label for="person-gender">Giới tính *</label>
                <select id="person-gender" name="gender" required>
                    <option value="">-- Chọn --</option>
                    <option value="MALE">Nam</option>
                    <option value="FEMALE">Nữ</option>
                </select>
            </div>
            <div class="form-group">
                <label for="person-cid">CMND/CCCD *</label>
                <input type="text" id="person-cid" name="cid" required maxlength="12">
            </div>
            <div class="form-group">
                <label for="person-household">Hộ khẩu</label>
                <select id="person-household" name="household_id">
                    <option value="">-- Chọn hộ khẩu --</option>
                    ${State.households.map(h => `
                        <option value="${h.id}">${h.household_code} - ${h.address}</option>
                    `).join('')}
                </select>
            </div>
            <div class="form-group">
                <label for="person-relation">Quan hệ với chủ hộ</label>
                <input type="text" id="person-relation" name="relation_to_owner" placeholder="VD: Chủ hộ, Vợ/Chồng, Con">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Thêm</button>
            </div>
        </form>
    `);
}

async function handleAddPerson(event) {
    event.preventDefault();

    const formData = {
        full_name: document.getElementById('person-name').value,
        dob: document.getElementById('person-dob').value,
        gender: document.getElementById('person-gender').value,
        cid: document.getElementById('person-cid').value,
        household_id: document.getElementById('person-household').value || null,
        relation_to_owner: document.getElementById('person-relation').value || null,
        status: 'PERMANENT'
    };

    try {
        showLoading();
        const result = await apiCall('/persons', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (result) {
            showToast('Đã thêm nhân khẩu mới', 'success');
            closeModal();
            loadPersons();
        }
    } catch (error) {
        console.error('Error adding person:', error);
    } finally {
        hideLoading();
    }
}

async function editPerson(id) {
    const person = State.persons.find(p => p.id === id);
    if (!person) {
        showToast('Không tìm thấy nhân khẩu', 'error');
        return;
    }

    showModal('Chỉnh sửa nhân khẩu', `
        <form id="edit-person-form" onsubmit="handleEditPerson(event, ${id})">
            <div class="form-group">
                <label for="edit-person-name">Họ và tên *</label>
                <input type="text" id="edit-person-name" value="${person.full_name || ''}" required>
            </div>
            <div class="form-group">
                <label for="edit-person-dob">Ngày sinh *</label>
                <input type="date" id="edit-person-dob" value="${person.dob || ''}" required>
            </div>
            <div class="form-group">
                <label for="edit-person-gender">Giới tính *</label>
                <select id="edit-person-gender" required>
                    <option value="MALE" ${person.gender === 'MALE' ? 'selected' : ''}>Nam</option>
                    <option value="FEMALE" ${person.gender === 'FEMALE' ? 'selected' : ''}>Nữ</option>
                </select>
            </div>
            <div class="form-group">
                <label for="edit-person-cid">CMND/CCCD *</label>
                <input type="text" id="edit-person-cid" value="${person.cid || ''}" required maxlength="12">
            </div>
            <div class="form-group">
                <label for="edit-person-household">Hộ khẩu</label>
                <select id="edit-person-household">
                    <option value="">-- Chọn hộ khẩu --</option>
                    ${State.households.map(h => `
                        <option value="${h.id}" ${person.household_id == h.id ? 'selected' : ''}>
                            ${h.household_code} - ${h.address}
                        </option>
                    `).join('')}
                </select>
            </div>
            <div class="form-group">
                <label for="edit-person-relation">Quan hệ với chủ hộ</label>
                <input type="text" id="edit-person-relation" value="${person.relation_to_owner || ''}">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Lưu</button>
            </div>
        </form>
    `);
}

async function handleEditPerson(event, id) {
    event.preventDefault();

    const formData = {
        full_name: document.getElementById('edit-person-name').value,
        dob: document.getElementById('edit-person-dob').value,
        gender: document.getElementById('edit-person-gender').value,
        cid: document.getElementById('edit-person-cid').value,
        household_id: document.getElementById('edit-person-household').value || null,
        relation_to_owner: document.getElementById('edit-person-relation').value || null
    };

    try {
        showLoading();
        const result = await apiCall(`/persons/${id}`, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });

        if (result) {
            showToast('Đã cập nhật nhân khẩu', 'success');
            closeModal();
            loadPersons();
        }
    } catch (error) {
        console.error('Error editing person:', error);
    } finally {
        hideLoading();
    }
}

async function deletePerson(id, name) {
    if (!confirm(`Bạn có chắc chắn muốn xóa nhân khẩu "${name}"?`)) {
        return;
    }

    try {
        showLoading();
        await apiCall(`/persons/${id}`, { method: 'DELETE' });
        showToast('Đã xóa nhân khẩu', 'success');
        loadPersons();
    } catch (error) {
        console.error('Error deleting person:', error);
    } finally {
        hideLoading();
    }
}

// Persons Pagination
function updatePersonsPagination(totalItems) {
    PersonsPagination.totalItems = totalItems;
    PersonsPagination.currentPage = 1;
    renderCurrentPersonsPage();
}

function renderCurrentPersonsPage() {
    const start = (PersonsPagination.currentPage - 1) * PersonsPagination.itemsPerPage;
    const end = start + PersonsPagination.itemsPerPage;
    const pageData = State.persons.slice(start, end);

    renderPersonsTable(pageData);
    renderPersonsPagination(State.persons);
}

function renderPersonsPagination(allPersons) {
    const totalPages = Math.ceil(PersonsPagination.totalItems / PersonsPagination.itemsPerPage);

    if (totalPages <= 1) {
        const el = document.getElementById('persons-pagination-container');
        if (el) el.innerHTML = '';
        return;
    }

    let paginationHTML = '<div class="pagination">';

    paginationHTML += `
        <button class="pagination-btn" 
                onclick="changePersonsPage(${PersonsPagination.currentPage - 1})"
                ${PersonsPagination.currentPage === 1 ? 'disabled' : ''}>
            ‹ Trước
        </button>
    `;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= PersonsPagination.currentPage - 1 && i <= PersonsPagination.currentPage + 1)) {
            paginationHTML += `
                <button class="pagination-btn ${i === PersonsPagination.currentPage ? 'active' : ''}"
                        onclick="changePersonsPage(${i})">
                    ${i}
                </button>
            `;
        } else if (i === PersonsPagination.currentPage - 2 || i === PersonsPagination.currentPage + 2) {
            paginationHTML += '<span class="pagination-dots">...</span>';
        }
    }

    paginationHTML += `
        <button class="pagination-btn" 
                onclick="changePersonsPage(${PersonsPagination.currentPage + 1})"
                ${PersonsPagination.currentPage === totalPages ? 'disabled' : ''}>
            Sau ›
        </button>
    `;

    paginationHTML += '</div>';

    const paginationContainer = document.getElementById('persons-pagination-container');
    if (paginationContainer) paginationContainer.innerHTML = paginationHTML;
}

function changePersonsPage(page) {
    const totalPages = Math.ceil(PersonsPagination.totalItems / PersonsPagination.itemsPerPage);

    if (page < 1 || page > totalPages) return;

    PersonsPagination.currentPage = page;
    renderCurrentPersonsPage();
}


// ==========================================
// PHASE 4: TEMPORARY ABSENCE & RESIDENCE
// ==========================================

State.absentRequests = [];
State.tempResidences = [];
State.currentSubTab = 'absent';

// Sub-tab switching
function switchSubTab(subtab) {
    // Update button states
    document.querySelectorAll('.sub-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Hide all subtab contents
    document.querySelectorAll('.subtab-content').forEach(content => {
        content.classList.add('hidden');
    });

    // Show selected subtab
    if (subtab === 'absent') {
        document.getElementById('absent-subtab').classList.remove('hidden');
        State.currentSubTab = 'absent';
        loadAbsentRequests();
    } else if (subtab === 'residence') {
        document.getElementById('residence-subtab').classList.remove('hidden');
        State.currentSubTab = 'residence';
        loadTempResidences();
    }
}

// ==========================================
// ABSENT REQUESTS
// ==========================================

async function loadAbsentRequests() {
    try {
        showLoading();
        const data = await apiCall('/absent-requests');

        if (data) {
            State.absentRequests = data;
            renderAbsentTable(data);
        }
    } catch (error) {
        console.error('Error loading absent requests:', error);
        document.querySelector('#absent-table tbody').innerHTML = `
            <tr>
                <td colspan="7" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">❌</div>
                    <p>Không thể tải dữ liệu</p>
                </td>
            </tr>
        `;
    } finally {
        hideLoading();
    }
}

function renderAbsentTable(requests) {
    const tbody = document.querySelector('#absent-table tbody');

    if (!requests || requests.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">📤</div>
                    <p>Chưa có yêu cầu tạm vắng nào</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = requests.map(req => {
        const person = State.persons.find(p => p.id === req.resident_id);
        const personName = person ? person.full_name : `Resident #${req.resident_id}`;

        const statusClass = req.status === 'APPROVED' ? 'status-approved' :
            req.status === 'REJECTED' ? 'status-rejected' : 'status-pending';
        const statusText = req.status === 'APPROVED' ? 'Đã duyệt' :
            req.status === 'REJECTED' ? 'Đã từ chối' : 'Chờ duyệt';

        let actions = '';
        if (req.status === 'PENDING' && State.user && (State.user.role === 'admin' || State.user.role === 'leader')) {
            actions = `
                <button class="icon-btn edit" onclick="approveAbsentRequest(${req.id})" title="Duyệt" style="color: var(--green-edit);">
                    ✓
                </button>
                <button class="icon-btn delete" onclick="rejectAbsentRequest(${req.id})" title="Từ chối">
                    ✗
                </button>
            `;
        }

        return `
        <tr>
            <td>${personName}</td>
            <td>${formatDate(req.start_date)}</td>
            <td>${formatDate(req.end_date)}</td>
            <td>${req.reason || ''}</td>
            <td>${req.destination || ''}</td>
            <td class="text-center">
                <span class="status-badge ${statusClass}">${statusText}</span>
            </td>
            <td class="text-right">
                <div class="action-icons">
                    ${actions}
                </div>
            </td>
        </tr>
    `}).join('');
}

function addAbsentRequest() {
    showModal('Tạo yêu cầu tạm vắng', `
        <form id="add-absent-form" onsubmit="handleAddAbsentRequest(event)">
            <div class="form-group">
                <label for="absent-resident">Nhân khẩu *</label>
                <select id="absent-resident" required>
                    <option value="">-- Chọn nhân khẩu --</option>
                    ${State.persons.map(p => `
                        <option value="${p.id}">${p.full_name} - ${p.cid}</option>
                    `).join('')}
                </select>
            </div>
            <div class="form-group">
                <label for="absent-start">Ngày bắt đầu *</label>
                <input type="date" id="absent-start" required>
            </div>
            <div class="form-group">
                <label for="absent-end">Ngày kết thúc *</label>
                <input type="date" id="absent-end" required>
            </div>
            <div class="form-group">
                <label for="absent-reason">Lý do *</label>
                <textarea id="absent-reason" rows="3" required placeholder="Lý do tạm vắng..."></textarea>
            </div>
            <div class="form-group">
                <label for="absent-destination">Địa điểm đến *</label>
                <input type="text" id="absent-destination" required placeholder="Địa chỉ tạm trú">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Tạo yêu cầu</button>
            </div>
        </form>
    `);
}

async function handleAddAbsentRequest(event) {
    event.preventDefault();

    const formData = {
        resident_id: parseInt(document.getElementById('absent-resident').value),
        start_date: document.getElementById('absent-start').value,
        end_date: document.getElementById('absent-end').value,
        reason: document.getElementById('absent-reason').value,
        destination: document.getElementById('absent-destination').value
    };

    try {
        showLoading();
        const result = await apiCall('/absent-requests', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (result) {
            showToast('Đã tạo yêu cầu tạm vắng', 'success');
            closeModal();
            loadAbsentRequests();
        }
    } catch (error) {
        console.error('Error creating absent request:', error);
    } finally {
        hideLoading();
    }
}

async function approveAbsentRequest(id) {
    if (!confirm('Bạn có chắc chắn muốn duyệt yêu cầu này?')) {
        return;
    }

    try {
        showLoading();
        await apiCall(`/absent-requests/${id}/approve`, {
            method: 'POST'
        });
        showToast('Đã duyệt yêu cầu', 'success');
        loadAbsentRequests();
    } catch (error) {
        console.error('Error approving request:', error);
    } finally {
        hideLoading();
    }
}

async function rejectAbsentRequest(id) {
    if (!confirm('Bạn có chắc chắn muốn từ chối yêu cầu này?')) {
        return;
    }

    showToast('Tính năng từ chối đang được phát triển', 'info');
    // TODO: Implement reject endpoint
}

// ==========================================
// TEMP RESIDENCE
// ==========================================

async function loadTempResidences() {
    try {
        showLoading();
        const data = await apiCall('/temp-residences');

        if (data) {
            State.tempResidences = data;
            renderResidenceTable(data);
        }
    } catch (error) {
        console.error('Error loading temp residences:', error);
        document.querySelector('#residence-table tbody').innerHTML = `
            <tr>
                <td colspan="7" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">❌</div>
                    <p>Không thể tải dữ liệu</p>
                </td>
            </tr>
        `;
    } finally {
        hideLoading();
    }
}

function renderResidenceTable(residences) {
    const tbody = document.querySelector('#residence-table tbody');

    if (!residences || residences.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">📥</div>
                    <p>Chưa có đăng ký tạm trú nào</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = residences.map(res => {
        const household = State.households.find(h => h.id === res.host_household_id);
        const householdCode = household ? household.household_code : 'N/A';

        const statusClass = res.status === 'APPROVED' ? 'status-approved' :
            res.status === 'REJECTED' ? 'status-rejected' : 'status-pending';
        const statusText = res.status === 'APPROVED' ? 'Đã duyệt' :
            res.status === 'REJECTED' ? 'Đã từ chối' : 'Chờ duyệt';

        let actions = '';
        if (res.status === 'PENDING' && State.user && (State.user.role === 'admin' || State.user.role === 'leader')) {
            actions = `
                <button class="icon-btn edit" onclick="approveTempResidence(${res.id})" title="Duyệt" style="color: var(--green-edit);">
                    ✓
                </button>
                <button class="icon-btn delete" onclick="rejectTempResidence(${res.id})" title="Từ chối">
                    ✗
                </button>
            `;
        }

        return `
        <tr>
            <td>${res.full_name || ''}</td>
            <td>${formatDate(res.dob)}</td>
            <td>${res.origin_address || ''}</td>
            <td>${householdCode}</td>
            <td>${formatDate(res.start_date)} - ${formatDate(res.end_date)}</td>
            <td class="text-center">
                <span class="status-badge ${statusClass}">${statusText}</span>
            </td>
            <td class="text-right">
                <div class="action-icons">
                    ${actions}
                </div>
            </td>
        </tr>
    `}).join('');
}

function addTempResidence() {
    showModal('Đăng ký tạm trú mới', `
        <form id="add-residence-form" onsubmit="handleAddTempResidence(event)">
            <div class="form-group">
                <label for="residence-name">Họ và tên *</label>
                <input type="text" id="residence-name" required>
            </div>
            <div class="form-group">
                <label for="residence-dob">Ngày sinh *</label>
                <input type="date" id="residence-dob" required>
            </div>
            <div class="form-group">
                <label for="residence-origin">Địa chỉ gốc *</label>
                <input type="text" id="residence-origin" required placeholder="Địa chỉ thường trú">
            </div>
            <div class="form-group">
                <label for="residence-household">Hộ khẩu tiếp nhận *</label>
                <select id="residence-household" required>
                    <option value="">-- Chọn hộ khẩu --</option>
                    ${State.households.map(h => `
                        <option value="${h.id}">${h.household_code} - ${h.address}</option>
                    `).join('')}
                </select>
            </div>
            <div class="form-group">
                <label for="residence-start">Ngày bắt đầu *</label>
                <input type="date" id="residence-start" required>
            </div>
            <div class="form-group">
                <label for="residence-end">Ngày kết thúc *</label>
                <input type="date" id="residence-end" required>
            </div>
            <div class="form-group">
                <label for="residence-reason">Lý do *</label>
                <textarea id="residence-reason" rows="3" required placeholder="Lý do tạm trú..."></textarea>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Đăng ký</button>
            </div>
        </form>
    `);
}

async function handleAddTempResidence(event) {
    event.preventDefault();

    const formData = {
        full_name: document.getElementById('residence-name').value,
        dob: document.getElementById('residence-dob').value,
        origin_address: document.getElementById('residence-origin').value,
        host_household_id: parseInt(document.getElementById('residence-household').value),
        start_date: document.getElementById('residence-start').value,
        end_date: document.getElementById('residence-end').value,
        reason: document.getElementById('residence-reason').value
    };

    try {
        showLoading();
        const result = await apiCall('/temp-residences', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (result) {
            showToast('Đã tạo đăng ký tạm trú', 'success');
            closeModal();
            loadTempResidences();
        }
    } catch (error) {
        console.error('Error creating temp residence:', error);
    } finally {
        hideLoading();
    }
}

async function approveTempResidence(id) {
    if (!confirm('Bạn có chắc chắn muốn duyệt đăng ký này?')) {
        return;
    }

    try {
        showLoading();
        await apiCall(`/temp-residences/${id}/approve`, {
            method: 'POST'
        });
        showToast('Đã duyệt đăng ký', 'success');
        loadTempResidences();
    } catch (error) {
        console.error('Error approving residence:', error);
    } finally {
        hideLoading();
    }
}

async function rejectTempResidence(id) {
    if (!confirm('Bạn có chắc chắn muốn từ chối đăng ký này?')) {
        return;
    }

    showToast('Tính năng từ chối đang được phát triển', 'info');
    // TODO: Implement reject endpoint
}

// ==========================================
// UI HELPERS
// ==========================================

function showModal(title, content) {
    const existing = document.querySelector('.modal-overlay');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>${title}</h3>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body">
                ${content}
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Close on backdrop click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Close on ESC key
    document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', escHandler);
        }
    });
}

function closeModal(modalId) {
    const modal = modalId ? document.getElementById(modalId) : document.querySelector('.modal-overlay');
    if (modal) {
        modal.remove();
    }
}

function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => toast.remove(), 3000);
}

function showLoading() {
    if (document.querySelector('.loading-overlay')) return;

    const loading = document.createElement('div');
    loading.className = 'loading-overlay';
    loading.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loading);
}

function hideLoading() {
    const loading = document.querySelector('.loading-overlay');
    if (loading) loading.remove();
}

// Context-aware Add button
function showAddModal() {
    switch (State.currentTab) {
        case 'households':
            addHousehold();
            break;
        case 'persons':
            addPerson();
            break;
        case 'complaints':
            addComplaint();
            break;
        default:
            showToast('Chọn một mục để thêm', 'info');
    }
}

// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', function () {
    console.log('Vietnamese Admin Dashboard initialized');

    // Check authentication
    if (checkAuth()) {
        showDashboard();
    } else {
        // Hide main dashboard, show login
        document.querySelector('.sidebar').style.display = 'none';
        document.querySelector('.main-wrapper').style.display = 'none';
        document.getElementById('auth-overlay').style.display = 'flex';
    }
});

// Inline login function for the HTML form
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('login-error');

    if (!username || !password) {
        errorEl.textContent = 'Vui lòng nhập đầy đủ thông tin';
        errorEl.style.display = 'block';
        return;
    }

    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
        showLoading();

        const response = await fetch('/api/token', {
            method: 'POST',
            body: formData,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Sai tên đăng nhập hoặc mật khẩu' }));
            throw new Error(err.detail || 'Sai tên đăng nhập hoặc mật khẩu');
        }

        const data = await response.json();

        // Save token
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', username);

        // Parse token to get user info
        const payload = parseJwt(data.access_token);
        State.token = data.access_token;
        State.user = { username, ...payload };

        // Show dashboard
        showDashboard();
        showToast('Đăng nhập thành công!', 'success');
        errorEl.style.display = 'none';

    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.style.display = 'block';
    } finally {
        hideLoading();
    }
}

// ==========================================
// PHASE 5: COMPLAINTS MANAGEMENT  
// ==========================================

State.complaints = [];

async function loadComplaints() {
    try {
        showLoading();
        const data = await apiCall('/complaints');

        if (data) {
            State.complaints = data;
            renderComplaintsTable(data);
        }
    } catch (error) {
        console.error('Error loading complaints:', error);
        document.querySelector('#complaints-table tbody').innerHTML = `
            <tr>
                <td colspan="6" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">❌</div>
                    <p>Không thể tải dữ liệu</p>
                </td>
            </tr>
        `;
    } finally {
        hideLoading();
    }
}

function renderComplaintsTable(complaints) {
    const tbody = document.querySelector('#complaints-table tbody');

    if (!complaints || complaints.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">📢</div>
                    <p>Chưa có phản ánh nào</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = complaints.map(c => {
        const categoryMap = {
            'SECURITY': 'An ninh',
            'HYGIENE': 'Vệ sinh',
            'INFRASTRUCTURE': 'Hạ tầng'
        };

        const statusClass = c.status === 'RESOLVED' ? 'badge badge-success' :
            c.status === 'PENDING' ? 'badge badge-warning' : 'badge badge-danger';
        const statusText = c.status === 'RESOLVED' ? 'Đã giải quyết' :
            c.status === 'PENDING' ? 'Đang xử lý' : 'Mới';

        // Impact Badge Logic
        const impactBadge = c.duplication_count > 0
            ? `<span class="impact-badge">x${c.duplication_count + 1} Reports</span>`
            : `<span class="badge badge-neutral">1 Report</span>`;

        // Truncate content
        const contentPreview = (c.content || '').length > 60 ?
            c.content.substring(0, 60) + '...' : c.content;

        let actions = `
            <button class="icon-btn" onclick="viewComplaintDetails(${c.id})" title="Xem chi tiết">
                👁️
            </button>
        `;

        if (State.user && (State.user.role === 'admin' || State.user.role === 'leader')) {
            if (c.status !== 'RESOLVED') {
                actions += `
                    <button class="icon-btn" onclick="updateComplaintStatus(${c.id}, 'PENDING')" title="Đang xử lý" style="color: var(--warning);">
                        🔄
                    </button>
                    <button class="icon-btn" onclick="updateComplaintStatus(${c.id}, 'RESOLVED')" title="Giải quyết" style="color: var(--success);">
                        ✓
                    </button>
                `;
            }
        }

        return `
        <tr>
            <td>
                <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">${categoryMap[c.category] || c.category}</div>
                <div style="color: var(--text-secondary); font-size: 13px;">${contentPreview}</div>
            </td>
            <td>${categoryMap[c.category]}</td>
            <td>${impactBadge}</td>
            <td style="color: var(--text-secondary);">${formatDate(c.created_at)}</td>
            <td>
                <span class="${statusClass}">${statusText}</span>
            </td>
            <td class="text-right">
                <div class="action-icons">
                    ${actions}
                </div>
            </td>
        </tr>
    `}).join('');

    // Update sidebar badge
    const activeCount = complaints.filter(c => c.status !== 'RESOLVED').length;
    const badge = document.getElementById('complaints-count');
    if (badge) {
        badge.textContent = activeCount;
        badge.style.display = activeCount > 0 ? 'inline-block' : 'none';
    }
}

function filterComplaints() {
    const category = document.getElementById('complaint-category-filter').value;
    const status = document.getElementById('complaint-status-filter').value;

    let filtered = State.complaints;

    if (category) {
        filtered = filtered.filter(c => c.category === category);
    }

    if (status) {
        filtered = filtered.filter(c => c.status === status);
    }

    renderComplaintsTable(filtered);
}

function addComplaint() {
    showModal('Tạo phản ánh mới', `
        <form id="add-complaint-form" onsubmit="handleAddComplaint(event)">
            <div class="form-group">
                <label for="complaint-category">Danh mục *</label>
                <select id="complaint-category" required>
                    <option value="">-- Chọn danh mục --</option>
                    <option value="SECURITY">An ninh & An toàn</option>
                    <option value="HYGIENE">Vệ sinh & Môi trường</option>
                    <option value="INFRASTRUCTURE">Cơ sở hạ tầng</option>
                </select>
            </div>
            <div class="form-group">
                <label for="complaint-content">Nội dung *</label>
                <textarea id="complaint-content" rows="5" required placeholder="Mô tả chi tiết vấn đề..."></textarea>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Gửi phản ánh</button>
            </div>
        </form>
    `);
}

async function handleAddComplaint(event) {
    event.preventDefault();

    const formData = {
        category: document.getElementById('complaint-category').value,
        content: document.getElementById('complaint-content').value
    };

    try {
        showLoading();
        const result = await apiCall('/complaints', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (result) {
            if (result.status === 'deduplicated') {
                showToast('Phản ánh tương tự đã tồn tại. Đã cập nhật số lượng.', 'info');
            } else {
                showToast('Đã gửi phản ánh thành công', 'success');
            }
            closeModal();
            loadComplaints();
        }
    } catch (error) {
        console.error('Error creating complaint:', error);
    } finally {
        hideLoading();
    }
}

async function viewComplaintDetails(id) {
    const complaint = State.complaints.find(c => c.id === id);
    if (!complaint) return;

    const categoryMap = {
        'SECURITY': 'An ninh & An toàn',
        'HYGIENE': 'Vệ sinh & Môi trường',
        'INFRASTRUCTURE': 'Cơ sở hạ tầng'
    };

    const statusText = complaint.status === 'RESOLVED' ? 'Đã giải quyết' :
        complaint.status === 'PENDING' ? 'Đang xử lý' : 'Mới';

    showModal('Chi tiết phản ánh', `
        <div>
            <div style="margin-bottom: 16px;">
                <strong>Danh mục:</strong> ${categoryMap[complaint.category]}
            </div>
            <div style="margin-bottom: 16px;">
                <strong>Trạng thái:</strong> <span class="status-badge">${statusText}</span>
            </div>
            <div style="margin-bottom: 16px;">
                <strong>Ngày tạo:</strong> ${formatDate(complaint.created_at)}
            </div>
            ${complaint.duplication_count > 0 ? `
                <div style="margin-bottom: 16px;">
                    <strong>Số lượng phản ánh tương tự:</strong> ${complaint.duplication_count}
                </div>
            ` : ''}
            <div style="margin-bottom: 16px;">
                <strong>Nội dung:</strong>
                <div style="padding: 12px; background: #f5f5f5; border-radius: 6px; margin-top: 8px;">
                    ${complaint.content}
                </div>
            </div>
            ${complaint.resolution_note ? `
                <div style="margin-bottom: 16px;">
                    <strong>Ghi chú giải quyết:</strong>
                    <div style="padding: 12px; background: #e8f5e9; border-radius: 6px; margin-top: 8px;">
                        ${complaint.resolution_note}
                    </div>
                </div>
            ` : ''}
        </div>
        <div class="modal-footer">
            <button type="button" class="btn-secondary" onclick="closeModal()">Đóng</button>
        </div>
    `);
}

async function updateComplaintStatus(id, newStatus) {
    const statusText = newStatus === 'RESOLVED' ? 'giải quyết' : 'đánh dấu đang xử lý';

    if (!confirm(`Bạn có chắc chắn muốn ${statusText} phản ánh này?`)) {
        return;
    }

    // If resolving, ask for note
    if (newStatus === 'RESOLVED') {
        const note = prompt('Nhập ghi chú giải quyết:');
        if (!note) return;

        try {
            showLoading();
            await apiCall(`/complaints/${id}`, {
                method: 'PUT',
                body: JSON.stringify({
                    status: newStatus,
                    resolution_note: note
                })
            });
            showToast('Đã cập nhật trạng thái', 'success');
            loadComplaints();
        } catch (error) {
            console.error('Error updating complaint:', error);
        } finally {
            hideLoading();
        }
    } else {
        try {
            showLoading();
            await apiCall(`/complaints/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ status: newStatus })
            });
            showToast('Đã cập nhật trạng thái', 'success');
            loadComplaints();
        } catch (error) {
            console.error('Error updating complaint:', error);
        } finally {
            hideLoading();
        }
    }
}

// ==========================================
// PHASE 6: STATISTICS & CHARTS
// ==========================================

let genderChart = null;
let ageChart = null;
let complaintsChart = null;

async function loadStatistics() {
    try {
        showLoading();

        // Load summary counts from API
        const summary = await apiCall('/stats/summary');
        if (summary) {
            document.getElementById('total-households').textContent = summary.total_households || 0;
            document.getElementById('total-persons').textContent = summary.total_persons || 0;
            document.getElementById('total-absent').textContent = `${summary.total_absent || 0} / ${summary.total_temp_residence || 0}`;
            document.getElementById('total-complaints').textContent = summary.pending_complaints || 0;
            const badge = document.getElementById('complaints-count');
            if (badge) badge.textContent = summary.pending_complaints || 0;
        }

        // Load population stats
        try {
            const popStats = await apiCall('/stats/population');
            if (popStats) {
                renderGenderChart(popStats.gender_distribution);
                renderAgeChart(popStats.age_distribution);
            }
        } catch (e) {
            console.log('Population stats not available:', e.message);
        }

        // Load complaints stats
        try {
            const complaintStats = await apiCall('/stats/complaints-quarterly');
            if (complaintStats) {
                renderComplaintsChart(complaintStats);
            }
        } catch (e) {
            console.log('Complaint stats not available:', e.message);
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    } finally {
        hideLoading();
    }
}

function renderGenderChart(data) {
    const ctx = document.getElementById('gender-chart');
    if (!ctx) return;

    // Destroy existing chart
    if (genderChart) {
        genderChart.destroy();
    }

    const maleCount = data?.MALE || 0;
    const femaleCount = data?.FEMALE || 0;

    genderChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Nam', 'Nữ'],
            datasets: [{
                data: [maleCount, femaleCount],
                backgroundColor: [
                    'rgba(6, 182, 212, 0.8)', // Teal
                    'rgba(239, 68, 68, 0.8)'  // Red/Pink for contrast or change to Navy
                ],
                borderColor: [
                    'rgba(6, 182, 212, 1)',
                    'rgba(239, 68, 68, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            family: 'Roboto, sans-serif',
                            size: 14
                        }
                    }
                },
                title: {
                    display: false
                }
            }
        }
    });
}

function renderAgeChart(data) {
    const ctx = document.getElementById('age-chart');
    if (!ctx) return;

    // Destroy existing chart
    if (ageChart) {
        ageChart.destroy();
    }

    const labels = [];
    const counts = [];

    // Expected format: {"0-18": 10, "19-35": 20, ...}
    const ageGroups = ['0-18', '19-35', '36-60', '60+'];
    ageGroups.forEach(group => {
        labels.push(group);
        counts.push(data?.[group] || 0);
    });

    ageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Số lượng',
                data: counts,
                backgroundColor: 'rgba(59, 130, 246, 0.8)', // Blue
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: {
                            family: 'Roboto, sans-serif'
                        }
                    }
                },
                x: {
                    ticks: {
                        font: {
                            family: 'Roboto, sans-serif'
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function renderComplaintsChart(data) {
    const ctx = document.getElementById('complaints-chart');
    if (!ctx) return;

    // Destroy existing chart
    if (complaintsChart) {
        complaintsChart.destroy();
    }

    // Expected format: array of {quarter, status, count}
    // Transform to: quarters as labels, 3 datasets (new, pending, resolved)

    const quarters = [...new Set(data.map(d => d.quarter))].sort();

    const newData = quarters.map(q => {
        const item = data.find(d => d.quarter === q && d.status === 'NEW');
        return item ? item.count : 0;
    });

    const pendingData = quarters.map(q => {
        const item = data.find(d => d.quarter === q && d.status === 'PENDING');
        return item ? item.count : 0;
    });

    const resolvedData = quarters.map(q => {
        const item = data.find(d => d.quarter === q && d.status === 'RESOLVED');
        return item ? item.count : 0;
    });

    complaintsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: quarters,
            datasets: [
                {
                    label: 'Mới',
                    data: newData,
                    borderColor: 'rgba(239, 68, 68, 1)', // Red
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Đang xử lý',
                    data: pendingData,
                    borderColor: 'rgba(245, 158, 11, 1)', // Amber
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Đã giải quyết',
                    data: resolvedData,
                    borderColor: 'rgba(16, 185, 129, 1)', // Green
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: {
                            family: 'Roboto, sans-serif'
                        }
                    }
                },
                x: {
                    ticks: {
                        font: {
                            family: 'Roboto, sans-serif'
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            family: 'Roboto, sans-serif',
                            size: 14
                        }
                    }
                }
            }
        }
    });
}
