// ==========================================
// VIETNAMESE ADMIN DASHBOARD - COMPLETE APP
// ==========================================

// ==========================================
// GLOBAL STATE
// ==========================================
const State = {
    user: null,
    token: null,
    role: null, // 'admin', 'leader', or 'resident'
    currentTab: 'statistics',
    households: [],
    persons: [],
    absentRequests: [],
    tempResidences: [],
    complaints: [],
    requests: [], // New: resident requests
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
    // Must check before query parameters
    const collectionRoutes = ['/households', '/persons', '/complaints', '/questions', '/reminders'];
    for (const route of collectionRoutes) {
        const fullRoute = API_BASE + route;
        if (url.startsWith(fullRoute)) {
            const charAfter = url[fullRoute.length];
            // If character after route is nothing, ?, or already /, add slash if needed
            if (!charAfter || charAfter === '?') {
                url = fullRoute + '/' + url.substring(fullRoute.length);
                break;
            }
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

// Switch between Login and Register tabs
function switchAuthTab(tab) {
    const loginTab = document.getElementById('login-tab');
    const registerTab = document.getElementById('register-tab');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    if (tab === 'login') {
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
        loginForm.style.display = 'flex';
        registerForm.style.display = 'none';
    } else {
        loginTab.classList.remove('active');
        registerTab.classList.add('active');
        loginForm.style.display = 'none';
        registerForm.style.display = 'flex';
    }

    // Clear any error/success messages
    document.getElementById('login-error').textContent = '';
    document.getElementById('register-error').textContent = '';
    document.getElementById('register-success').textContent = '';
}

// Toggle CCCD/Verification code fields based on role
function toggleRoleFields() {
    const role = document.getElementById('reg-role').value;
    const cccdField = document.getElementById('cccd-field');
    const verificationField = document.getElementById('verification-field');
    const newResidentFields = document.getElementById('new-resident-fields');

    if (role === 'resident') {
        cccdField.style.display = 'block';
        verificationField.style.display = 'none';
        // Hide new resident fields until CCCD is checked
        if (newResidentFields) newResidentFields.style.display = 'none';
    } else {
        cccdField.style.display = 'none';
        verificationField.style.display = 'block';
        if (newResidentFields) newResidentFields.style.display = 'none';
    }

    // Clear CCCD status
    const statusEl = document.getElementById('cccd-status');
    if (statusEl) statusEl.textContent = '';
}

// Check if CCCD exists in system
async function checkCCCD() {
    const cccd = document.getElementById('reg-cccd').value.trim();
    const statusEl = document.getElementById('cccd-status');
    const newResidentFields = document.getElementById('new-resident-fields');

    if (!cccd || cccd.length !== 12) {
        statusEl.textContent = '';
        if (newResidentFields) newResidentFields.style.display = 'none';
        return;
    }

    try {
        const response = await fetch('/api/check-cccd', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cccd })
        });

        const data = await response.json();

        if (data.exists) {
            if (data.has_account) {
                statusEl.innerHTML = '<span style="color: #ef4444;">⚠️ CCCD này đã có tài khoản</span>';
                if (newResidentFields) newResidentFields.style.display = 'none';
            } else {
                statusEl.innerHTML = `<span style="color: #22c55e;">✓ Tìm thấy: ${data.resident_name}</span>`;
                if (newResidentFields) newResidentFields.style.display = 'none';
            }
        } else {
            statusEl.innerHTML = '<span style="color: #3b82f6;">📝 CCCD mới - Vui lòng nhập thông tin cá nhân</span>';
            if (newResidentFields) newResidentFields.style.display = 'block';
        }
    } catch (error) {
        statusEl.textContent = '';
        if (newResidentFields) newResidentFields.style.display = 'none';
    }
}

// Register new user
async function register() {
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const role = document.getElementById('reg-role').value;
    const cccd = document.getElementById('reg-cccd').value.trim();
    const verificationCode = document.getElementById('reg-code').value.trim();

    // New resident fields
    const fullName = document.getElementById('reg-fullname')?.value.trim() || '';
    const dob = document.getElementById('reg-dob')?.value || '';
    const gender = document.getElementById('reg-gender')?.value || '';

    const errorEl = document.getElementById('register-error');
    const successEl = document.getElementById('register-success');

    errorEl.textContent = '';
    successEl.textContent = '';

    // Client-side validation
    if (!username || !password) {
        errorEl.textContent = 'Vui lòng nhập tên đăng nhập và mật khẩu';
        return;
    }

    if (password.length < 6) {
        errorEl.textContent = 'Mật khẩu phải có ít nhất 6 ký tự';
        return;
    }

    if (role === 'resident' && !cccd) {
        errorEl.textContent = 'Vui lòng nhập số CCCD';
        return;
    }

    if ((role === 'admin' || role === 'leader') && !verificationCode) {
        errorEl.textContent = 'Vui lòng nhập mã xác minh';
        return;
    }

    try {
        showLoading();

        const requestBody = {
            username,
            password,
            role,
            cccd: role === 'resident' ? cccd : null,
            verification_code: (role === 'admin' || role === 'leader') ? verificationCode : null
        };

        // Add new resident fields if they exist
        if (role === 'resident' && fullName) {
            requestBody.full_name = fullName;
            requestBody.dob = dob;
            requestBody.gender = gender;
        }

        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Đăng ký thất bại');
        }

        successEl.textContent = data.message;

        // Clear form
        document.getElementById('reg-username').value = '';
        document.getElementById('reg-password').value = '';
        document.getElementById('reg-cccd').value = '';
        document.getElementById('reg-code').value = '';
        if (document.getElementById('reg-fullname')) document.getElementById('reg-fullname').value = '';
        if (document.getElementById('reg-dob')) document.getElementById('reg-dob').value = '';
        if (document.getElementById('reg-gender')) document.getElementById('reg-gender').value = '';

        const statusEl = document.getElementById('cccd-status');
        if (statusEl) statusEl.textContent = '';
        const newResidentFields = document.getElementById('new-resident-fields');
        if (newResidentFields) newResidentFields.style.display = 'none';

        showToast('Đăng ký thành công!', 'success');

        // Switch to login tab after 2 seconds
        setTimeout(() => {
            switchAuthTab('login');
        }, 2000);

    } catch (error) {
        errorEl.textContent = error.message;
    } finally {
        hideLoading();
    }
}

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

        // Save token and role
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', username);
        localStorage.setItem('role', data.role || 'resident');

        // Parse token to get user info
        const payload = parseJwt(data.access_token);
        State.token = data.access_token;
        State.user = { username, ...payload };
        State.role = data.role || payload.role || 'resident';

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
    localStorage.removeItem('role');
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
    State.role = localStorage.getItem('role') || payload.role || 'resident';
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

    // Apply role-based visibility
    applyRoleBasedUI();

    // Load notifications
    loadNotifications();
}

// ==========================================
// NOTIFICATION SYSTEM
// ==========================================

async function loadNotifications() {
    try {
        const notifications = await apiCall('/my/notifications');
        if (notifications) {
            renderNotificationDropdown(notifications);
            updateNotificationBadge(notifications);
        }
    } catch (error) {
        console.log('Notifications not available:', error.message);
    }
}

function renderNotificationDropdown(notifications) {
    const container = document.getElementById('notification-list');
    if (!container) return;

    if (!notifications || notifications.length === 0) {
        container.innerHTML = '<div style="padding: 24px; text-align: center; color: #64748b;">Không có thông báo mới</div>';
        return;
    }

    container.innerHTML = notifications.slice(0, 10).map(n => `
        <div class="notification-item" data-id="${n.id}" onclick="viewNotification(${n.id})"
             style="padding: 12px 16px; border-bottom: 1px solid #f1f5f9; cursor: pointer; ${!n.is_read ? 'background: #f0f9ff;' : ''}">
            <div style="display: flex; gap: 12px;">
                <div style="font-size: 20px;">${getNotificationIcon(n.type)}</div>
                <div style="flex: 1;">
                    <div style="font-weight: ${!n.is_read ? '600' : '400'}; color: #1e293b; font-size: 13px;">${n.title}</div>
                    <div style="color: #64748b; font-size: 12px; margin-top: 2px;">${formatTimeAgo(n.created_at)}</div>
                </div>
                ${!n.is_read ? '<div style="width: 8px; height: 8px; background: #3b82f6; border-radius: 50%; margin-top: 4px;"></div>' : ''}
            </div>
        </div>
    `).join('');
}

function getNotificationIcon(type) {
    const icons = {
        'INFO': 'ℹ️',
        'REMINDER': '⏰',
        'REQUEST': '📋',
        'COMPLAINT': '📢',
        'SYSTEM': '⚙️'
    };
    return icons[type] || '🔔';
}

function updateNotificationBadge(notifications) {
    const badge = document.getElementById('notification-badge');
    if (!badge) return;

    const unreadCount = notifications.filter(n => !n.is_read).length;
    badge.textContent = unreadCount;
    badge.style.display = unreadCount > 0 ? 'block' : 'none';
}

function toggleNotificationDropdown() {
    const dropdown = document.getElementById('notification-dropdown');
    if (dropdown) {
        dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
    }
}

async function viewNotification(id) {
    try {
        await apiCall(`/my/notifications/${id}/read`, 'PUT');
        loadNotifications();
    } catch (error) {
        console.log('Could not mark notification as read:', error.message);
    }
}

function formatTimeAgo(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;

    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes} phút trước`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} giờ trước`;

    const days = Math.floor(hours / 24);
    if (days < 7) return `${days} ngày trước`;

    return formatDate(dateStr);
}

// Close dropdown when clicking outside
document.addEventListener('click', function (e) {
    const dropdown = document.getElementById('notification-dropdown');
    const btn = document.getElementById('btn-notifications');
    if (dropdown && btn && !dropdown.contains(e.target) && !btn.contains(e.target)) {
        dropdown.style.display = 'none';
    }
});

function updateUserDisplay() {
    if (State.user) {
        const nameEl = document.getElementById('user-display-name');
        if (nameEl) nameEl.textContent = State.user.username;

        const roleEl = document.querySelector('.user-role');
        if (roleEl) {
            const roleNames = {
                'admin': 'Quản trị viên',
                'leader': 'Tổ trưởng',
                'resident': 'Cư dân'
            };
            roleEl.textContent = roleNames[State.role] || 'Người dùng';
        }

        const avatarEl = document.querySelector('.avatar');
        if (avatarEl && State.user.username) {
            avatarEl.textContent = State.user.username.substring(0, 2).toUpperCase();
        }
    }
}

function applyRoleBasedUI() {
    const role = State.role;
    const navItems = document.querySelectorAll('.nav-item');

    // Admin/Leader tabs to hide for residents
    const adminOnlyTabs = ['statistics', 'households', 'persons'];

    // Tabs only for admin (not even leader)
    const adminExclusiveTabs = ['users'];

    navItems.forEach(item => {
        const dataTab = item.getAttribute('data-tab') || '';

        // Hide admin-only tabs for residents
        if (adminOnlyTabs.includes(dataTab)) {
            item.style.display = (role === 'resident') ? 'none' : 'flex';
        }

        // Hide admin-exclusive tabs for non-admins
        if (adminExclusiveTabs.includes(dataTab)) {
            item.style.display = (role === 'admin') ? 'flex' : 'none';
        }

        // Show my-household only for residents
        if (dataTab === 'my-household') {
            item.style.display = (role === 'resident') ? 'flex' : 'none';
        }
    });

    updateActionButtons();

    // Set default tab based on role
    if (role === 'resident') {
        switchTab('my-household');
    } else {
        switchTab('statistics');
    }
}

function updateActionButtons() {
    const role = State.role;
    const addBtn = document.querySelector('.header-actions .btn-primary');
    const viewRequestsBtn = document.getElementById('btn-view-requests');

    // Show/hide view requests button (leaders and admins only)
    if (viewRequestsBtn) {
        viewRequestsBtn.style.display = (role === 'leader' || role === 'admin') ? 'inline-flex' : 'none';
    }

    // Configure the main action button based on role
    if (addBtn) {
        if (role === 'resident') {
            addBtn.innerHTML = '<span>+</span> Tạo yêu cầu';
            addBtn.setAttribute('onclick', 'showRequestModal()');
        } else {
            addBtn.innerHTML = '<span>+</span> Thêm mới';
            addBtn.setAttribute('onclick', 'showAddModal()');
        }
    }
}

// Admin/Leader: Show modal to select what to add
function showAddModal() {
    showModal('Chọn loại thêm mới', `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <button class="btn-add" style="padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 8px;" onclick="closeModal(); addHousehold();">
                <span style="font-size: 28px;">🏠</span>
                <span>Thêm hộ khẩu</span>
            </button>
            <button class="btn-add" style="padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 8px;" onclick="closeModal(); addPerson();">
                <span style="font-size: 28px;">👤</span>
                <span>Thêm nhân khẩu</span>
            </button>
            <button class="btn-add" style="padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 8px;" onclick="closeModal(); addTempResidence();">
                <span style="font-size: 28px;">📋</span>
                <span>Thêm tạm trú</span>
            </button>
            <button class="btn-add" style="padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 8px;" onclick="closeModal(); addAbsentRequest();">
                <span style="font-size: 28px;">🚶</span>
                <span>Thêm tạm vắng</span>
            </button>
            <button class="btn-add" style="padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 8px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);" onclick="closeModal(); showSplitHouseholdForm();">
                <span style="font-size: 28px;">✂️</span>
                <span>Tách hộ khẩu</span>
            </button>
        </div>
        <div class="modal-footer" style="margin-top: 20px;">
            <button type="button" class="btn-secondary" onclick="closeModal()">Đóng</button>
        </div>
    `);
}

// ==========================================
// REQUEST SYSTEM (Role-based)
// ==========================================

// For Residents: Create a new request
function showRequestModal() {
    // Pre-load households for forms that need them
    if (!State.households || State.households.length === 0) {
        loadHouseholds();
    }

    showModal('Tạo yêu cầu mới', `
        <form id="create-request-form" onsubmit="handleCreateRequest(event)">
            <div class="form-group">
                <label for="request-type">Loại yêu cầu *</label>
                <select id="request-type" required onchange="toggleRequestFields()">
                    <option value="">-- Chọn loại --</option>
                    <option value="SPLIT_HOUSEHOLD">Yêu cầu tách khẩu</option>
                    <option value="JOIN_HOUSEHOLD">Yêu cầu nhập khẩu</option>
                    <option value="NEW_HOUSEHOLD">Yêu cầu tạo hộ khẩu mới</option>
                    <option value="PERSON_UPDATE">Cập nhật thông tin cá nhân</option>
                    <option value="OTHER">Yêu cầu khác</option>
                </select>
            </div>
            <div class="form-group">
                <label for="request-title">Tiêu đề *</label>
                <input type="text" id="request-title" required placeholder="Nhập tiêu đề yêu cầu">
            </div>
            
            <!-- Dynamic fields for SPLIT_HOUSEHOLD -->
            <div id="split-fields" class="dynamic-fields" style="display: none;">
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <h4 style="margin: 0 0 12px 0; color: #475569;">📋 Thông tin tách khẩu</h4>
                    <div class="form-group">
                        <label>Địa chỉ hộ khẩu mới *</label>
                        <input type="text" id="req-new-address" class="form-control" placeholder="Nhập địa chỉ hộ khẩu mới" required>
                    </div>
                    <div class="form-group">
                        <label>Mã hộ khẩu mới (đề xuất)</label>
                        <input type="text" id="req-new-code" class="form-control" placeholder="VD: HK-2024-001">
                        <small style="color: #64748b;">Để trống nếu muốn hệ thống tự tạo</small>
                    </div>
                </div>
            </div>
            
            <!-- Dynamic fields for JOIN_HOUSEHOLD -->
            <div id="join-fields" class="dynamic-fields" style="display: none;">
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <h4 style="margin: 0 0 12px 0; color: #475569;">📋 Thông tin nhập khẩu</h4>
                    <div class="form-group">
                        <label>Mã hộ khẩu muốn nhập vào *</label>
                        <input type="text" id="req-target-hh-code" class="form-control" placeholder="Nhập mã hộ khẩu đích" required>
                    </div>
                    <div class="form-group">
                        <label>Quan hệ với chủ hộ *</label>
                        <select id="req-relation" class="form-control">
                            <option value="MEMBER">Thành viên</option>
                            <option value="WIFE">Vợ</option>
                            <option value="HUSBAND">Chồng</option>
                            <option value="SON">Con trai</option>
                            <option value="DAUGHTER">Con gái</option>
                            <option value="PARENT">Bố/Mẹ</option>
                            <option value="GRANDPARENT">Ông/Bà</option>
                            <option value="SIBLING">Anh/Chị/Em</option>
                        </select>
                    </div>
                </div>
            </div>
            
            <!-- Dynamic fields for NEW_HOUSEHOLD -->
            <div id="new-hh-fields" class="dynamic-fields" style="display: none;">
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <h4 style="margin: 0 0 12px 0; color: #475569;">📋 Thông tin hộ khẩu mới</h4>
                    <div class="form-group">
                        <label>Địa chỉ hộ khẩu mới *</label>
                        <input type="text" id="req-new-hh-address" class="form-control" placeholder="Nhập địa chỉ đầy đủ" required>
                    </div>
                    <div class="form-group">
                        <label>Mã hộ khẩu mới (đề xuất)</label>
                        <input type="text" id="req-new-hh-code" class="form-control" placeholder="VD: HK-2024-001">
                        <small style="color: #64748b;">Để trống nếu muốn hệ thống tự tạo</small>
                    </div>
                </div>
            </div>
            
            <!-- Dynamic fields for PERSON_UPDATE -->
            <div id="person-update-fields" class="dynamic-fields" style="display: none;">
                <div style="background: #f8fafc; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <h4 style="margin: 0 0 12px 0; color: #475569;">📋 Thông tin cần cập nhật</h4>
                    <div class="form-group">
                        <label>Họ và tên mới</label>
                        <input type="text" id="req-new-name" class="form-control" placeholder="Để trống nếu không đổi">
                    </div>
                    <div class="form-group">
                        <label>Ngày sinh mới</label>
                        <input type="date" id="req-new-dob" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Giới tính</label>
                        <select id="req-new-gender" class="form-control">
                            <option value="">-- Không thay đổi --</option>
                            <option value="MALE">Nam</option>
                            <option value="FEMALE">Nữ</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Số CCCD mới</label>
                        <input type="text" id="req-new-cid" class="form-control" placeholder="Số CCCD 12 số">
                    </div>
                </div>
            </div>
            

            <div class="form-group">
                <label for="request-content">Lý do / Ghi chú thêm *</label>
                <textarea id="request-content" rows="3" required placeholder="Mô tả lý do và các thông tin bổ sung nếu có..."></textarea>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Gửi yêu cầu</button>
            </div>
        </form>
    `);
}

function toggleRequestFields() {
    const type = document.getElementById('request-type').value;

    // Hide all dynamic fields first
    document.querySelectorAll('.dynamic-fields').forEach(el => {
        el.style.display = 'none';
        // Remove required from hidden fields
        el.querySelectorAll('input, select, textarea').forEach(input => {
            input.removeAttribute('data-was-required');
            if (input.hasAttribute('required')) {
                input.setAttribute('data-was-required', 'true');
                input.removeAttribute('required');
            }
        });
    });

    // Show relevant fields and restore required
    let targetFields = null;
    if (type === 'SPLIT_HOUSEHOLD') {
        targetFields = document.getElementById('split-fields');
    } else if (type === 'JOIN_HOUSEHOLD') {
        targetFields = document.getElementById('join-fields');
    } else if (type === 'NEW_HOUSEHOLD') {
        targetFields = document.getElementById('new-hh-fields');
    } else if (type === 'PERSON_UPDATE') {
        targetFields = document.getElementById('person-update-fields');
    }

    if (targetFields) {
        targetFields.style.display = 'block';
        // Restore required attributes
        targetFields.querySelectorAll('[data-was-required="true"]').forEach(input => {
            input.setAttribute('required', '');
        });
    }
}

async function handleCreateRequest(event) {
    event.preventDefault();

    const requestType = document.getElementById('request-type').value;
    const title = document.getElementById('request-title').value;
    const description = document.getElementById('request-content').value;

    // Build request_data based on request type
    let requestData = {};

    if (requestType === 'SPLIT_HOUSEHOLD') {
        const newAddress = document.getElementById('req-new-address').value;
        const newCode = document.getElementById('req-new-code').value;
        requestData = {
            new_address: newAddress,
            new_household_code: newCode || `HK-${Date.now()}`
        };
    } else if (requestType === 'JOIN_HOUSEHOLD') {
        const targetCode = document.getElementById('req-target-hh-code').value;
        const relation = document.getElementById('req-relation').value;
        const targetHH = State.households.find(h => h.household_code === targetCode);
        requestData = {
            target_household_code: targetCode,
            target_household_id: targetHH ? targetHH.id : null,
            relation_to_owner: relation
        };
    } else if (requestType === 'NEW_HOUSEHOLD') {
        const newAddress = document.getElementById('req-new-hh-address').value;
        const newCode = document.getElementById('req-new-hh-code').value;
        requestData = {
            address: newAddress,
            household_code: newCode || `HK-${Date.now()}`
        };
    } else if (requestType === 'PERSON_UPDATE') {
        const newName = document.getElementById('req-new-name').value;
        const newDob = document.getElementById('req-new-dob').value;
        const newGender = document.getElementById('req-new-gender').value;
        const newCid = document.getElementById('req-new-cid').value;
        requestData = {};
        if (newName) requestData.full_name = newName;
        if (newDob) requestData.dob = newDob;
        if (newGender) requestData.gender = newGender;
        if (newCid) requestData.cid = newCid;
    }

    const formData = {
        request_type: requestType,
        title: title,
        description: description,
        request_data: JSON.stringify(requestData)
    };

    try {
        showLoading();
        const result = await apiCall('/requests/', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (result) {
            showToast('Đã gửi yêu cầu thành công! Vui lòng chờ duyệt.', 'success');
            closeModal();
            if (State.currentTab === 'my-household') {
                loadMyRequests();
            }
        }
    } catch (error) {
        console.error('Error creating request:', error);
    } finally {
        hideLoading();
    }
}

// For Leaders/Admins: View and process pending requests
async function showPendingRequests() {
    try {
        showLoading();
        const requests = await apiCall('/requests/?status_filter=PENDING');

        if (!requests || requests.length === 0) {
            showModal('Yêu cầu chờ duyệt', `
                <div style="text-align: center; padding: 40px;">
                    <div class="empty-state-icon">📋</div>
                    <p>Không có yêu cầu nào đang chờ duyệt</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-secondary" onclick="closeModal()">Đóng</button>
                </div>
            `);
            return;
        }

        const requestTypeLabels = {
            'NEW_HOUSEHOLD': 'Tạo hộ khẩu mới',
            'JOIN_HOUSEHOLD': 'Nhập khẩu',
            'SPLIT_HOUSEHOLD': 'Tách khẩu',
            'HOUSEHOLD_UPDATE': 'Thay đổi HK',
            'PERSON_UPDATE': 'Cập nhật TT',
            'TEMP_RESIDENCE': 'Tạm trú',
            'TEMP_ABSENCE': 'Tạm vắng',
            'OTHER': 'Khác'
        };

        const requestsHtml = requests.map(req => `
            <div class="request-item" style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <div>
                        <span class="badge badge-info">${requestTypeLabels[req.request_type] || req.request_type}</span>
                        <strong style="margin-left: 8px;">${req.title}</strong>
                    </div>
                    <span style="color: #64748b; font-size: 12px;">${formatDate(req.created_at)}</span>
                </div>
                <p style="color: #475569; margin-bottom: 8px;">${req.description || ''}</p>
                <p style="color: #94a3b8; font-size: 12px; margin-bottom: 12px;">Người gửi: ${req.requester_name || 'N/A'}</p>
                <div style="display: flex; gap: 8px;">
                    <button class="btn-add" style="padding: 6px 12px; font-size: 12px;" onclick="approveRequest(${req.id})">
                        ✓ Duyệt
                    </button>
                    <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px; color: #ef4444;" onclick="rejectRequest(${req.id})">
                        ✗ Từ chối
                    </button>
                </div>
            </div>
        `).join('');

        showModal('Yêu cầu chờ duyệt (' + requests.length + ')', `
            <div style="max-height: 400px; overflow-y: auto;">
                ${requestsHtml}
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Đóng</button>
            </div>
        `);
    } catch (error) {
        console.error('Error loading requests:', error);
        showToast('Không thể tải danh sách yêu cầu', 'error');
    } finally {
        hideLoading();
    }
}

async function approveRequest(id) {
    if (!confirm('Bạn có chắc chắn muốn duyệt yêu cầu này?')) {
        return;
    }

    try {
        showLoading();
        await apiCall(`/requests/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ status: 'APPROVED' })
        });
        showToast('Đã duyệt yêu cầu', 'success');
        closeModal();
        showPendingRequests(); // Refresh the list
    } catch (error) {
        console.error('Error approving request:', error);
    } finally {
        hideLoading();
    }
}

async function rejectRequest(id) {
    const reason = prompt('Nhập lý do từ chối:');
    if (!reason) return;

    try {
        showLoading();
        await apiCall(`/requests/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ status: 'REJECTED', approval_note: reason })
        });
        showToast('Đã từ chối yêu cầu', 'success');
        closeModal();
        showPendingRequests(); // Refresh the list
    } catch (error) {
        console.error('Error rejecting request:', error);
    } finally {
        hideLoading();
    }
}

// ==========================================
// TAB SWITCHING
// ==========================================

function switchTab(tabName) {
    // Close all open modals when switching tabs
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });

    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        // Use data-tab attribute for matching
        if (item.getAttribute('data-tab') === tabName) {
            item.classList.add('active');
        }
    });

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    const content = document.getElementById('tab-' + tabName);
    if (content) {
        content.classList.add('active');
        State.currentTab = tabName;

        const pageTitles = {
            'statistics': 'Tổng quan Tổ dân phố',
            'households': 'Quản lý Hộ khẩu',
            'persons': 'Quản lý Nhân khẩu',
            'my-household': 'Hộ khẩu của tôi',
            'temporary': 'Quản lý Tạm trú / Tạm vắng',
            'complaints': 'Phản ánh & Kiến nghị',
            'questions': 'Hỏi đáp với Tổ trưởng / Admin',
            'reminders': 'Nhắc nhở thông minh'
        };
        document.getElementById('page-title').textContent = pageTitles[tabName] || 'Dashboard';
    }

    if (tabName === 'households') {
        loadHouseholds();
    } else if (tabName === 'persons') {
        loadPersons();
    } else if (tabName === 'my-household') {
        loadMyHouseholdData();
    } else if (tabName === 'temporary') {
        loadAbsentRequests();
        loadTempResidences();
    } else if (tabName === 'complaints') {
        loadComplaints();
    } else if (tabName === 'statistics') {
        loadStatistics();
    } else if (tabName === 'questions') {
        loadQuestions();
    } else if (tabName === 'reminders') {
        loadReminders();
    } else if (tabName === 'users') {
        loadUsers();
        loadRolesFilter();
    }
}

// ==========================================
// USER MANAGEMENT (Admin Only)
// ==========================================

let usersData = [];
let rolesData = [];

async function loadUsers() {
    try {
        showLoading();
        const roleId = document.getElementById('user-role-filter')?.value || '';
        const isActive = document.getElementById('user-status-filter')?.value || '';

        let url = '/admin/users';
        const params = new URLSearchParams();
        if (roleId) params.append('role_id', roleId);
        if (isActive) params.append('is_active', isActive);
        if (params.toString()) url += '?' + params.toString();

        const users = await apiCall(url);
        if (users) {
            usersData = users;
            renderUsersTable(users);
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showToast('Chỉ admin mới có quyền truy cập', 'error');
    } finally {
        hideLoading();
    }
}

async function loadRolesFilter() {
    try {
        const roles = await apiCall('/admin/roles');
        if (roles) {
            rolesData = roles;
            const select = document.getElementById('user-role-filter');
            if (select) {
                const currentValue = select.value;
                select.innerHTML = '<option value="">Tất cả vai trò</option>' +
                    roles.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
                select.value = currentValue;
            }
        }
    } catch (error) {
        console.log('Could not load roles');
    }
}

function filterUsers() {
    loadUsers();
}

function renderUsersTable(users) {
    const tbody = document.querySelector('#users-table tbody');
    if (!tbody) return;

    if (!users || users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">👥</div>
                    <p>Không tìm thấy người dùng</p>
                </td>
            </tr>
        `;
        return;
    }

    const roleColors = {
        'admin': '#ef4444',
        'leader': '#3b82f6',
        'resident': '#10b981'
    };

    const roleLabels = {
        'admin': 'Admin',
        'leader': 'Tổ trưởng',
        'resident': 'Cư dân'
    };

    tbody.innerHTML = users.map(u => {
        const roleColor = roleColors[u.role_name?.toLowerCase()] || '#64748b';
        const roleLabel = roleLabels[u.role_name?.toLowerCase()] || u.role_name || 'N/A';
        const statusClass = u.is_active ? 'badge-success' : 'badge-danger';
        const statusText = u.is_active ? 'Hoạt động' : 'Vô hiệu hóa';

        let actions = `
            <button class="icon-btn" onclick="showEditUserModal(${u.id})" title="Sửa">✏️</button>
        `;

        // Can't edit self
        if (u.id !== State.user?.user_id) {
            if (u.is_active) {
                actions += `<button class="icon-btn" onclick="toggleUserStatus(${u.id}, false)" title="Vô hiệu hóa" style="color: var(--warning);">⛔</button>`;
            } else {
                actions += `<button class="icon-btn" onclick="toggleUserStatus(${u.id}, true)" title="Kích hoạt" style="color: var(--success);">✓</button>`;
            }
            actions += `<button class="icon-btn" onclick="confirmDeleteUser(${u.id})" title="Xóa" style="color: var(--danger);">🗑️</button>`;
        }

        return `
            <tr>
                <td><strong>${u.username}</strong></td>
                <td><span class="badge" style="background-color: ${roleColor}; color: white;">${roleLabel}</span></td>
                <td>${u.resident_name || '<span style="color: #94a3b8;">Chưa liên kết</span>'}</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
                <td class="text-right">
                    <div class="action-icons">${actions}</div>
                </td>
            </tr>
        `;
    }).join('');
}

async function showCreateUserModal() {
    // Load roles first
    if (rolesData.length === 0) {
        await loadRolesFilter();
    }

    const roleOptions = rolesData.map(r => `<option value="${r.id}">${r.name}</option>`).join('');

    showModal('👤 Thêm người dùng mới', `
        <form id="create-user-form">
            <div class="form-group">
                <label class="form-label">Tên đăng nhập *</label>
                <input type="text" class="form-control" id="new-username" required>
            </div>
            <div class="form-group">
                <label class="form-label">Mật khẩu *</label>
                <input type="password" class="form-control" id="new-password" required>
            </div>
            <div class="form-group">
                <label class="form-label">Vai trò *</label>
                <select class="form-control" id="new-role-id" required>
                    ${roleOptions}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">
                    <input type="checkbox" id="new-is-active" checked> Kích hoạt ngay
                </label>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-primary" onclick="createUser(); return false;">Tạo người dùng</button>
            </div>
        </form>
    `);
}

async function createUser() {
    const username = document.getElementById('new-username').value.trim();
    const password = document.getElementById('new-password').value;
    const roleId = document.getElementById('new-role-id').value;
    const isActive = document.getElementById('new-is-active').checked;

    if (!username || !password || !roleId) {
        showToast('Vui lòng điền đầy đủ thông tin', 'error');
        return;
    }

    try {
        const result = await apiCall('/admin/users', 'POST', {
            username,
            password,
            role_id: parseInt(roleId),
            is_active: isActive
        });

        if (result) {
            showToast('Tạo người dùng thành công!', 'success');
            closeModal();
            loadUsers();
        }
    } catch (error) {
        showToast('Lỗi: ' + error.message, 'error');
    }
}

async function showEditUserModal(userId) {
    const user = usersData.find(u => u.id === userId);
    if (!user) {
        showToast('Không tìm thấy người dùng', 'error');
        return;
    }

    if (rolesData.length === 0) {
        await loadRolesFilter();
    }

    const roleOptions = rolesData.map(r =>
        `<option value="${r.id}" ${r.id === user.role_id ? 'selected' : ''}>${r.name}</option>`
    ).join('');

    const isSelf = userId === State.user?.user_id;

    showModal('✏️ Sửa người dùng', `
        <form id="edit-user-form">
            <div class="form-group">
                <label class="form-label">Tên đăng nhập</label>
                <input type="text" class="form-control" id="edit-username" value="${user.username}" ${isSelf ? '' : ''}>
            </div>
            <div class="form-group">
                <label class="form-label">Mật khẩu mới (để trống nếu không đổi)</label>
                <input type="password" class="form-control" id="edit-password" placeholder="••••••••">
            </div>
            <div class="form-group">
                <label class="form-label">Vai trò</label>
                <select class="form-control" id="edit-role-id" ${isSelf ? 'disabled' : ''}>
                    ${roleOptions}
                </select>
                ${isSelf ? '<small style="color: #64748b;">Không thể thay đổi vai trò của chính mình</small>' : ''}
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-primary" onclick="updateUser(${userId}); return false;">Lưu thay đổi</button>
            </div>
        </form>
    `);
}

async function updateUser(userId) {
    const data = {};

    const username = document.getElementById('edit-username').value.trim();
    const password = document.getElementById('edit-password').value;
    const roleSelect = document.getElementById('edit-role-id');

    if (username) data.username = username;
    if (password) data.password = password;
    if (roleSelect && !roleSelect.disabled) data.role_id = parseInt(roleSelect.value);

    try {
        const result = await apiCall(`/admin/users/${userId}`, 'PUT', data);
        if (result) {
            showToast('Cập nhật thành công!', 'success');
            closeModal();
            loadUsers();
        }
    } catch (error) {
        showToast('Lỗi: ' + error.message, 'error');
    }
}

async function toggleUserStatus(userId, isActive) {
    try {
        const result = await apiCall(`/admin/users/${userId}/status?is_active=${isActive}`, 'PUT');
        if (result) {
            showToast(result.message, 'success');
            loadUsers();
        }
    } catch (error) {
        showToast('Lỗi: ' + error.message, 'error');
    }
}

function confirmDeleteUser(userId) {
    const user = usersData.find(u => u.id === userId);
    showModal('⚠️ Xác nhận xóa', `
        <p>Bạn có chắc chắn muốn xóa người dùng <strong>${user?.username || userId}</strong>?</p>
        <p style="color: #ef4444;">Hành động này không thể hoàn tác!</p>
        <div class="modal-footer">
            <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
            <button type="button" class="btn-primary" style="background: #ef4444;" onclick="deleteUser(${userId})">Xóa</button>
        </div>
    `);
}

async function deleteUser(userId) {
    try {
        const result = await apiCall(`/admin/users/${userId}`, 'DELETE');
        if (result) {
            showToast('Đã xóa người dùng', 'success');
            closeModal();
            loadUsers();
        }
    } catch (error) {
        showToast('Lỗi: ' + error.message, 'error');
    }
}

// ==========================================
// MY HOUSEHOLD (Resident Self-Service)
// ==========================================

async function loadMyHouseholdData() {
    try {
        showLoading();
        // Load all data in parallel
        await Promise.all([
            loadMyProfile(),
            loadMyHousehold(),
            loadMyFamily(),
            loadMyRequests(),
            loadMyHistory()
        ]);
    } catch (error) {
        console.error('Error loading my household data:', error);
    } finally {
        hideLoading();
    }
}

async function loadMyHistory() {
    try {
        const history = await apiCall('/my/history');
        if (history) {
            renderPersonalHistory(history.personal || []);
            renderHouseholdHistory(history.household || []);
        }
    } catch (error) {
        console.log('History not available:', error.message);
    }
}

function renderPersonalHistory(items) {
    const container = document.getElementById('my-personal-history');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<p style="color: #64748b; text-align: center; padding: 16px;">Chưa có lịch sử thay đổi</p>';
        return;
    }

    container.innerHTML = items.map(item => `
        <div style="display: flex; align-items: center; padding: 12px; background: #f8fafc; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #3b82f6;">
            <div style="flex: 1;">
                <div style="font-weight: 600; color: #1e40af;">${item.change_type}</div>
                <div style="color: #64748b; font-size: 12px;">${item.details || 'Không có chi tiết'}</div>
            </div>
            <div style="text-align: right; color: #64748b; font-size: 12px;">
                <div>${formatDate(item.changed_at)}</div>
                <div>bởi ${item.changed_by || 'Hệ thống'}</div>
            </div>
        </div>
    `).join('');
}

function renderHouseholdHistory(items) {
    const container = document.getElementById('my-household-history');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<p style="color: #64748b; text-align: center; padding: 16px;">Chưa có lịch sử thay đổi</p>';
        return;
    }

    container.innerHTML = items.map(item => `
        <div style="display: flex; align-items: center; padding: 12px; background: #f0fdf4; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #10b981;">
            <div style="flex: 1;">
                <div style="font-weight: 600; color: #047857;">${item.change_type}</div>
                <div style="color: #64748b; font-size: 12px;">${item.details || 'Không có chi tiết'}</div>
            </div>
            <div style="text-align: right; color: #64748b; font-size: 12px;">
                <div>${formatDate(item.changed_at)}</div>
                <div>bởi ${item.changed_by || 'Hệ thống'}</div>
            </div>
        </div>
    `).join('');
}

async function loadMyProfile() {
    try {
        const profile = await apiCall('/my/profile');
        if (profile) {
            document.getElementById('my-profile-name').textContent = profile.full_name;
            document.getElementById('my-profile-details').textContent =
                `CCCD: ${profile.cid} | Ngày sinh: ${formatDate(profile.dob)} | ${profile.gender === 'MALE' ? 'Nam' : 'Nữ'} `;
        }
    } catch (error) {
        document.getElementById('my-profile-name').textContent = 'Chưa liên kết';
        document.getElementById('my-profile-details').textContent = 'Bạn chưa được liên kết với nhân khẩu';
    }
}

async function loadMyHousehold() {
    try {
        const household = await apiCall('/my/household');
        if (household) {
            document.getElementById('my-household-code').textContent = household.household_code;
            document.getElementById('my-household-address').textContent =
                `Địa chỉ: ${household.address} | Chủ hộ: ${household.owner_name || 'Chưa có'} | ${household.member_count} thành viên`;
        }
    } catch (error) {
        document.getElementById('my-household-code').textContent = '-';
        document.getElementById('my-household-address').textContent = 'Chưa thuộc hộ khẩu nào';
    }
}

async function loadMyFamily() {
    try {
        const family = await apiCall('/my/family');
        renderMyFamilyTable(family || []);
    } catch (error) {
        renderMyFamilyTable([]);
    }
}

function renderMyFamilyTable(members) {
    const tbody = document.querySelector('#my-family-table tbody');
    if (!tbody) return;

    if (!members || members.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 40px; color: #64748b;">
                    <div style="font-size: 48px; margin-bottom: 8px;">👨‍👩‍👧</div>
                    <p>Chưa có thông tin thành viên</p>
                </td>
            </tr>
        `;
        return;
    }

    const genderLabels = { 'MALE': 'Nam', 'FEMALE': 'Nữ' };
    const statusLabels = {
        'PERMANENT': 'Thường trú',
        'TEMPORARY': 'Tạm trú',
        'ABSENT': 'Tạm vắng'
    };
    const statusClasses = {
        'PERMANENT': 'badge-success',
        'TEMPORARY': 'badge-info',
        'ABSENT': 'badge-warning'
    };

    tbody.innerHTML = members.map(m => `
        <tr>
            <td><strong>${m.full_name}</strong></td>
            <td>${m.cid}</td>
            <td>${formatDate(m.dob)}</td>
            <td>${genderLabels[m.gender] || m.gender}</td>
            <td>${m.relation_to_owner}</td>
            <td><span class="badge ${statusClasses[m.status] || 'badge-secondary'}">${statusLabels[m.status] || m.status}</span></td>
        </tr>
    `).join('');
}

async function loadMyRequests() {
    try {
        const requests = await apiCall('/my/requests');
        renderMyRequestsTable(requests || []);
    } catch (error) {
        renderMyRequestsTable([]);
    }
}

function renderMyRequestsTable(requests) {
    const tbody = document.querySelector('#my-requests-table tbody');
    if (!tbody) return;

    if (!requests || requests.length === 0) {
        tbody.innerHTML = `
            < tr >
            <td colspan="5" style="text-align: center; padding: 40px; color: #64748b;">
                <div style="font-size: 48px; margin-bottom: 8px;">📝</div>
                <p>Bạn chưa có yêu cầu nào</p>
                <button class="btn-primary" onclick="showRequestModal()" style="margin-top: 12px;">+ Tạo yêu cầu mới</button>
            </td>
            </tr >
            `;
        return;
    }

    const typeLabels = {
        'NEW_HOUSEHOLD': 'Tạo HK mới',
        'JOIN_HOUSEHOLD': 'Nhập khẩu',
        'SPLIT_HOUSEHOLD': 'Tách khẩu',
        'PERSON_UPDATE': 'Cập nhật TT',
        'TEMP_RESIDENCE': 'Tạm trú',
        'TEMP_ABSENCE': 'Tạm vắng',
        'OTHER': 'Khác'
    };

    const statusLabels = {
        'PENDING': 'Chờ duyệt',
        'APPROVED': 'Đã duyệt',
        'REJECTED': 'Từ chối'
    };
    const statusClasses = {
        'PENDING': 'badge-warning',
        'APPROVED': 'badge-success',
        'REJECTED': 'badge-danger'
    };

    tbody.innerHTML = requests.map(r => `
            < tr >
            <td><span class="badge badge-info">${typeLabels[r.request_type] || r.request_type}</span></td>
            <td><strong>${r.title}</strong></td>
            <td>${formatDate(r.created_at)}</td>
            <td><span class="badge ${statusClasses[r.status] || 'badge-secondary'}">${statusLabels[r.status] || r.status}</span></td>
            <td style="color: ${r.status === 'REJECTED' ? '#ef4444' : '#64748b'};">${r.admin_note || '-'}</td>
        </tr >
            `).join('');
}

// ==========================================
// TEMPORARY RESIDENCE/ABSENCE MANAGEMENT
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
    } finally {
        hideLoading();
    }
}

function renderAbsentTable(requests) {
    const tableBody = document.querySelector('#absent-table tbody');
    if (!tableBody) return;

    if (!requests || requests.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #94a3b8;">Không có dữ liệu tạm vắng</td></tr>';
        return;
    }

    const statusLabels = {
        'PENDING': 'Chờ duyệt',
        'APPROVED': 'Đã duyệt',
        'REJECTED': 'Từ chối'
    };
    const statusClasses = {
        'PENDING': 'badge-warning',
        'APPROVED': 'badge-success',
        'REJECTED': 'badge-danger'
    };

    tableBody.innerHTML = requests.map(r => `
        <tr>
            <td>${r.resident_name || 'Cư dân #' + r.resident_id}</td>
            <td>${r.reason || '-'}</td>
            <td>${formatDate(r.start_date)} - ${formatDate(r.end_date)}</td>
            <td>
                <span class="badge ${statusClasses[r.status] || 'badge-secondary'}">${statusLabels[r.status] || r.status}</span>
                ${r.status === 'PENDING' && (State.role === 'leader' || State.role === 'admin') ?
            `<button class="btn-action" style="margin-left: 8px;" onclick="approveAbsentRequest(${r.id})">✓</button>` : ''}
            </td>
        </tr>
    `).join('');
}

async function loadTempResidences() {
    try {
        showLoading();
        const data = await apiCall('/temp-residences');
        if (data) {
            State.tempResidences = data;
            renderTempResidenceTable(data);
        }
    } catch (error) {
        console.error('Error loading temp residences:', error);
    } finally {
        hideLoading();
    }
}

function renderTempResidenceTable(registrations) {
    const tableBody = document.querySelector('#temp-res-table tbody');
    if (!tableBody) return;

    if (!registrations || registrations.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #94a3b8;">Không có dữ liệu tạm trú</td></tr>';
        return;
    }

    const statusLabels = {
        'PENDING': 'Chờ duyệt',
        'APPROVED': 'Đã duyệt',
        'REJECTED': 'Từ chối'
    };
    const statusClasses = {
        'PENDING': 'badge-warning',
        'APPROVED': 'badge-success',
        'REJECTED': 'badge-danger'
    };

    tableBody.innerHTML = registrations.map(r => `
        <tr>
            <td>${r.full_name}</td>
            <td>${r.origin_address || '-'}</td>
            <td>${r.reason || '-'}</td>
            <td>
                <span class="badge ${statusClasses[r.status] || 'badge-secondary'}">${statusLabels[r.status] || r.status}</span>
                ${r.status === 'PENDING' && (State.role === 'leader' || State.role === 'admin') ?
            `<button class="btn-action" style="margin-left: 8px;" onclick="approveTempResidence(${r.id})">✓</button>` : ''}
            </td>
        </tr>
    `).join('');
}

async function approveAbsentRequest(id) {
    if (!confirm('Duyệt yêu cầu tạm vắng này?')) return;
    try {
        showLoading();
        await apiCall(`/absent-requests/${id}/approve`, { method: 'POST' });
        showToast('Đã duyệt yêu cầu tạm vắng', 'success');
        loadAbsentRequests();
    } catch (error) {
        console.error('Error approving absent request:', error);
        showToast('Lỗi khi duyệt yêu cầu', 'error');
    } finally {
        hideLoading();
    }
}

async function approveTempResidence(id) {
    if (!confirm('Duyệt đăng ký tạm trú này?')) return;
    try {
        showLoading();
        await apiCall(`/temp-residences/${id}/approve`, { method: 'POST' });
        showToast('Đã duyệt đăng ký tạm trú', 'success');
        loadTempResidences();
    } catch (error) {
        console.error('Error approving temp residence:', error);
        showToast('Lỗi khi duyệt đăng ký', 'error');
    } finally {
        hideLoading();
    }
}

function addAbsentRequest() {
    const formHtml = `
        <form id="add-absent-form" onsubmit="handleAddAbsent(event)">
            <div class="form-group">
                <label>Cư dân (ID)</label>
                <input type="number" id="absent-resident-id" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Ngày bắt đầu</label>
                <input type="date" id="absent-start-date" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Ngày kết thúc</label>
                <input type="date" id="absent-end-date" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Lý do</label>
                <input type="text" id="absent-reason" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Nơi đến</label>
                <input type="text" id="absent-destination" class="form-control" required>
            </div>
            <button type="submit" class="btn-add" style="width: 100%; margin-top: 16px;">Đăng ký tạm vắng</button>
        </form>
    `;
    showModal('Đăng ký Tạm vắng', formHtml);
}

async function handleAddAbsent(event) {
    event.preventDefault();
    try {
        showLoading();
        await apiCall('/absent-requests', {
            method: 'POST',
            body: JSON.stringify({
                resident_id: parseInt(document.getElementById('absent-resident-id').value),
                start_date: document.getElementById('absent-start-date').value,
                end_date: document.getElementById('absent-end-date').value,
                reason: document.getElementById('absent-reason').value,
                destination: document.getElementById('absent-destination').value
            })
        });
        showToast('Đã đăng ký tạm vắng thành công', 'success');
        closeModal();
        loadAbsentRequests();
    } catch (error) {
        console.error('Error adding absent request:', error);
        showToast('Lỗi khi đăng ký tạm vắng', 'error');
    } finally {
        hideLoading();
    }
}

function addTempResidence() {
    const formHtml = `
        <form id="add-temp-res-form" onsubmit="handleAddTempRes(event)">
            <div class="form-group">
                <label>Họ và tên</label>
                <input type="text" id="temp-res-name" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Ngày sinh</label>
                <input type="date" id="temp-res-dob" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Địa chỉ gốc</label>
                <input type="text" id="temp-res-origin" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Hộ khẩu tiếp nhận (ID)</label>
                <input type="number" id="temp-res-host-id" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Ngày bắt đầu</label>
                <input type="date" id="temp-res-start" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Ngày kết thúc</label>
                <input type="date" id="temp-res-end" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Lý do</label>
                <input type="text" id="temp-res-reason" class="form-control" required>
            </div>
            <button type="submit" class="btn-add" style="width: 100%; margin-top: 16px;">Đăng ký tạm trú</button>
        </form>
    `;
    showModal('Đăng ký Tạm trú', formHtml);
}

async function handleAddTempRes(event) {
    event.preventDefault();
    try {
        showLoading();
        await apiCall('/temp-residences', {
            method: 'POST',
            body: JSON.stringify({
                full_name: document.getElementById('temp-res-name').value,
                dob: document.getElementById('temp-res-dob').value,
                origin_address: document.getElementById('temp-res-origin').value,
                host_household_id: parseInt(document.getElementById('temp-res-host-id').value),
                start_date: document.getElementById('temp-res-start').value,
                end_date: document.getElementById('temp-res-end').value,
                reason: document.getElementById('temp-res-reason').value
            })
        });
        showToast('Đã đăng ký tạm trú thành công', 'success');
        closeModal();
        loadTempResidences();
    } catch (error) {
        console.error('Error adding temp residence:', error);
        showToast('Lỗi khi đăng ký tạm trú', 'error');
    } finally {
        hideLoading();
    }
}

// ==========================================
// HOUSEHOLDS MANAGEMENT
// ==========================================


async function loadHouseholds() {
    try {
        showLoading();
        const response = await apiCall(`/households/?page=${Pagination.currentPage}&limit=${Pagination.itemsPerPage}`);

        if (response && response.items) {
            State.households = response.items;  // Store current page items
            Pagination.totalItems = response.total;
            Pagination.currentPage = response.page;

            renderHouseholdsTable(response.items);
            renderPagination();
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
                    <button class="action-btn" onclick="viewHouseholdHistory(${h.id})" title="Lịch sử thay đổi">📜</button>
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
                <input type="text" id="household-code" name="household_code" class="form-control" required placeholder="VD: HK001">
            </div>
            <div class="form-group">
                <label for="household-address">Địa chỉ *</label>
                <input type="text" id="household-address" name="address" class="form-control" required placeholder="Nhập địa chỉ đầy đủ">
            </div>
            <div class="form-group">
                <label for="owner-id">ID chủ hộ (tùy chọn)</label>
                <input type="number" id="owner-id" name="owner_id" class="form-control" placeholder="ID nhân khẩu sẽ làm chủ hộ">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-primary">Thêm hộ khẩu</button>
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
    const household = State.households.find(h => h.id === id);
    if (!household) {
        showToast('Không tìm thấy hộ khẩu', 'error');
        return;
    }

    showModal('Chỉnh sửa hộ khẩu', `
        <form id="edit-household-form" onsubmit="handleEditHousehold(event, ${id})">
            <div class="form-group">
                <label for="edit-household-code">Số hộ khẩu *</label>
                <input type="text" id="edit-household-code" name="household_code" class="form-control" value="${household.household_code || ''}" required>
            </div>
            <div class="form-group">
                <label for="edit-household-address">Địa chỉ *</label>
                <input type="text" id="edit-household-address" name="address" class="form-control" value="${household.address || ''}" required>
            </div>
            <div class="form-group">
                <label for="edit-owner-id">ID chủ hộ (tùy chọn)</label>
                <input type="number" id="edit-owner-id" name="owner_id" class="form-control" value="${household.owner_id || ''}">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-primary">Lưu thay đổi</button>
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
                <label for="split-old-household">Hộ khẩu cũ *</label>
                <select id="split-old-household" class="form-control" required onchange="updateResidentsList()">
                    <option value="">-- Chọn hộ khẩu --</option>
                    ${State.households.map(h => `
                        <option value="${h.id}">${h.household_code} - ${h.address}</option>
                    `).join('')}
                </select>
            </div>
            <div class="form-group">
                <label for="split-new-owner">ID chủ hộ mới *</label>
                <input type="number" id="split-new-owner" name="new_owner_id" class="form-control" required placeholder="ID người làm chủ hộ mới">
            </div>
            <div class="form-group">
                <label for="split-moving-ids">ID thành viên chuyển đi *</label>
                <input type="text" id="split-moving-ids" name="moving_resident_ids" class="form-control" required placeholder="VD: 1, 2, 3">
                <small class="text-muted">Nhập các ID cách nhau bởi dấu phẩy</small>
            </div>
            <div class="form-group">
                <label for="split-new-code">Số hộ khẩu mới *</label>
                <input type="text" id="split-new-code" name="new_household_code" class="form-control" required placeholder="VD: HK002">
            </div>
            <div class="form-group">
                <label for="split-new-address">Địa chỉ mới *</label>
                <input type="text" id="split-new-address" name="new_address" class="form-control" required placeholder="Địa chỉ hộ khẩu mới">
            </div>
            <div class="form-group">
                <label for="split-replacement-id">ID chủ hộ thay thế (nếu cần)</label>
                <input type="number" id="split-replacement-id" name="replacement_owner_id" class="form-control" placeholder="Chỉ cần nếu chủ hộ cũ chuyển đi">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-primary">Thực hiện tách hộ</button>
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
        <button class="pagination-btn" onclick="changePage(${Pagination.currentPage - 1})" ${Pagination.currentPage === 1 ? 'disabled' : ''}>
            ‹ Trước
        </button>
    `;

    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= Pagination.currentPage - 1 && i <= Pagination.currentPage + 1)) {
            paginationHTML += `
                <button class="pagination-btn ${i === Pagination.currentPage ? 'active' : ''}" onclick="changePage(${i})">
                    ${i}
                </button>
            `;
        } else if (i === Pagination.currentPage - 2 || i === Pagination.currentPage + 2) {
            paginationHTML += '<span class="pagination-dots">...</span>';
        }
    }

    // Next button
    paginationHTML += `
        <button class="pagination-btn" onclick="changePage(${Pagination.currentPage + 1})" ${Pagination.currentPage === totalPages ? 'disabled' : ''}>
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
    loadHouseholds();  // Fetch new page from server
}

function renderCurrentPage() {
    // This function is no longer needed for server-side pagination
    // Keeping for backwards compatibility but calls loadHouseholds
    loadHouseholds();
}

function updatePagination(totalItems) {
    Pagination.totalItems = totalItems;
    Pagination.currentPage = 1;
    renderPagination();
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

        // Load households first if not already loaded (needed for filter dropdown)
        if (!State.households || State.households.length === 0) {
            try {
                const householdsResponse = await apiCall('/households/?page=1&limit=1000');
                if (householdsResponse && householdsResponse.items) {
                    State.households = householdsResponse.items;
                }
            } catch (e) {
                console.log('Could not load households for filter:', e);
            }
        }

        const response = await apiCall(`/persons/?page=${PersonsPagination.currentPage}&limit=${PersonsPagination.itemsPerPage}`);

        if (response && response.items) {
            State.persons = response.items;  // Store current page items
            PersonsPagination.totalItems = response.total;
            PersonsPagination.currentPage = response.page;

            populateHouseholdFilter();
            renderPersonsTable(response.items);
            renderPersonsPagination(response.items);
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

    // Group persons by household for better display
    let currentHouseholdId = null;
    let html = '';

    persons.forEach(p => {
        // Add household header row when switching to a new household
        if (p.household_id !== currentHouseholdId) {
            currentHouseholdId = p.household_id;
            const householdCode = p.household_code || 'N/A';
            html += `
                <tr class="household-group-header" style="background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%);">
                    <td colspan="7" style="font-weight: 600; color: #0369a1; padding: 12px 16px;">
                        🏠 Hộ khẩu: <strong>${householdCode}</strong>
                    </td>
                </tr>
            `;
        }

        // Use household_code directly from response
        const householdCode = p.household_code || 'N/A';

        // Status badge
        const statusBadge = {
            'PERMANENT': '<span class="badge badge-success">Thường trú</span>',
            'TEMPORARY': '<span class="badge badge-warning">Tạm trú</span>',
            'ABSENT': '<span class="badge badge-info">Tạm vắng</span>'
        }[p.status] || '<span class="badge badge-neutral">Khác</span>';

        html += `
            <tr>
                <td>
                    <strong>${p.full_name || ''}</strong>
                    ${p.phone || p.email || p.occupation ? `
                        <div style="font-size: 0.85em; color: #666; margin-top: 4px;">
                            ${p.phone ? `📱 ${p.phone}` : ''}
                            ${p.email ? `<br>📧 ${p.email}` : ''}
                            ${p.occupation ? `<br>💼 ${p.occupation}` : ''}
                        </div>
                    ` : ''}
                </td>
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
        `;
    });

    tbody.innerHTML = html;
}

function populateHouseholdFilter() {
    const select = document.getElementById('household-filter');
    if (!select) return; // Guard against missing element

    const options = State.households.map(h =>
        `<option value="${h.id}">${h.household_code} - ${h.address}</option>`
    ).join('');

    select.innerHTML = `<option value="">--Tất cả hộ khẩu--</option>${options}`;
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
                <input type="text" id="person-name" name="full_name" class="form-control" required placeholder="Nhập họ và tên đầy đủ">
            </div>
            <div class="form-group">
                <label for="person-dob">Ngày sinh *</label>
                <input type="date" id="person-dob" name="dob" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="person-gender">Giới tính *</label>
                <select id="person-gender" name="gender" class="form-control" required>
                    <option value="">-- Chọn giới tính --</option>
                    <option value="MALE">Nam</option>
                    <option value="FEMALE">Nữ</option>
                </select>
            </div>
            <div class="form-group">
                <label for="person-cid">CMND/CCCD *</label>
                <input type="text" id="person-cid" name="cid" class="form-control" required maxlength="12" placeholder="Nhập 12 số CCCD">
            </div>
            <div class="form-group">
                <label for="person-household">Thuộc hộ khẩu</label>
                <select id="person-household" name="household_id" class="form-control">
                    <option value="">-- Chọn hộ khẩu --</option>
                    ${State.households.map(h => `
                        <option value="${h.id}">${h.household_code} - ${h.address}</option>
                    `).join('')}
                </select>
            </div>
            <div class="form-group">
                <label for="person-relation">Quan hệ với chủ hộ</label>
                <input type="text" id="person-relation" name="relation_to_owner" class="form-control" placeholder="VD: Chủ hộ, Vợ/Chồng, Con">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-primary">Thêm nhân khẩu</button>
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
                <input type="text" id="edit-person-name" class="form-control" value="${person.full_name || ''}" required>
            </div>
            <div class="form-group">
                <label for="edit-person-dob">Ngày sinh *</label>
                <input type="date" id="edit-person-dob" class="form-control" value="${person.dob || ''}" required>
            </div>
            <div class="form-group">
                <label for="edit-person-gender">Giới tính *</label>
                <select id="edit-person-gender" class="form-control" required>
                    <option value="MALE" ${person.gender === 'MALE' ? 'selected' : ''}>Nam</option>
                    <option value="FEMALE" ${person.gender === 'FEMALE' ? 'selected' : ''}>Nữ</option>
                </select>
            </div>
            <div class="form-group">
                <label for="edit-person-cid">CMND/CCCD *</label>
                <input type="text" id="edit-person-cid" class="form-control" value="${person.cid || ''}" required maxlength="12">
            </div>
            <div class="form-group">
                <label for="edit-person-household">Thuộc hộ khẩu</label>
                <select id="edit-person-household" class="form-control">
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
                <input type="text" id="edit-person-relation" class="form-control" value="${person.relation_to_owner || ''}">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-primary">Lưu thay đổi</button>
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
    if (!confirm(`Bạn có chắc chắn muốn xóa nhân khẩu "${name}" ? `)) {
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
    renderPersonsPagination();
}

function renderCurrentPersonsPage() {
    // No longer needed for server-side pagination
    // Keeping for backwards compatibility
    loadPersons();
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
        <button class="pagination-btn" onclick="changePersonsPage(${PersonsPagination.currentPage - 1})" ${PersonsPagination.currentPage === 1 ? 'disabled' : ''}>
            ‹ Trước
        </button>
    `;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= PersonsPagination.currentPage - 1 && i <= PersonsPagination.currentPage + 1)) {
            paginationHTML += `
                <button class="pagination-btn ${i === PersonsPagination.currentPage ? 'active' : ''}" onclick="changePersonsPage(${i})">
                    ${i}
                </button>
            `;
        } else if (i === PersonsPagination.currentPage - 2 || i === PersonsPagination.currentPage + 2) {
            paginationHTML += '<span class="pagination-dots">...</span>';
        }
    }

    paginationHTML += `
        <button class="pagination-btn" onclick="changePersonsPage(${PersonsPagination.currentPage + 1})" ${PersonsPagination.currentPage === totalPages ? 'disabled' : ''}>
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
    loadPersons();  // Fetch new page from server
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
            < tr >
            <td colspan="7" class="text-center" style="padding: 40px;">
                <div class="empty-state-icon">❌</div>
                <p>Không thể tải dữ liệu</p>
            </td>
            </tr >
            `;
    } finally {
        hideLoading();
    }
}

function renderAbsentTable(requests) {
    const tbody = document.querySelector('#absent-table tbody');

    if (!requests || requests.length === 0) {
        tbody.innerHTML = `
            < tr >
            <td colspan="7" class="text-center" style="padding: 40px;">
                <div class="empty-state-icon">📤</div>
                <p>Chưa có yêu cầu tạm vắng nào</p>
            </td>
            </tr >
            `;
        return;
    }

    tbody.innerHTML = requests.map(req => {
        const person = State.persons.find(p => p.id === req.resident_id);
        const personName = person ? person.full_name : `Resident #${req.resident_id} `;

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
        } else if (req.status === 'APPROVED' && State.user && (State.user.role === 'admin' || State.user.role === 'leader')) {
            actions = `
            <button class="icon-btn" onclick="generateAbsentCertificate(${req.id})" title="Xem giấy tạm vắng" style="color: var(--primary-blue);">
                📄
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
                <select id="absent-resident" class="form-control" required>
                    <option value="">-- Chọn nhân khẩu --</option>
                    ${State.persons.map(p => `
                        <option value="${p.id}">${p.full_name} - ${p.cid}</option>
                    `).join('')}
                </select>
            </div>
            <div class="form-group">
                <label for="absent-start">Ngày bắt đầu *</label>
                <input type="date" id="absent-start" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="absent-end">Ngày kết thúc *</label>
                <input type="date" id="absent-end" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="absent-reason">Lý do *</label>
                <textarea id="absent-reason" class="form-control" rows="3" required placeholder="Lý do tạm vắng..."></textarea>
            </div>
            <div class="form-group">
                <label for="absent-destination">Địa điểm đến *</label>
                <input type="text" id="absent-destination" class="form-control" required placeholder="Địa chỉ tạm trú">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-primary">Tạo yêu cầu</button>
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

    try {
        showLoading();
        await apiCall(`/absent-requests/${id}/reject`, {
            method: 'POST',
            body: JSON.stringify({})
        });
        showToast('Đã từ chối yêu cầu', 'success');
        loadAbsentRequests();
    } catch (error) {
        console.error('Error rejecting request:', error);
    } finally {
        hideLoading();
    }
}

async function generateAbsentCertificate(id) {
    try {
        showLoading();
        const cert = await apiCall(`/absent-requests/${id}/certificate`);

        if (cert) {
            showCertificateModal(cert);
        }
    } catch (error) {
        console.error('Error generating certificate:', error);
        showToast('Không thể tạo giấy tạm vắng', 'error');
    } finally {
        hideLoading();
    }
}

function showCertificateModal(cert) {
    const modalContent = `
        <div class="certificate-container" id="certificate-print-area">
            <div class="certificate-header">
                <h2>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h2>
                <p><strong>Độc lập - Tự do - Hạnh phúc</strong></p>
                <hr>
            </div>
            <div class="certificate-title">
                <h1>GIẤY XÁC NHẬN TẠM VẮNG</h1>
            </div>
            <div class="certificate-body">
                <p>Xác nhận công dân:</p>
                <table class="certificate-info">
                    <tr>
                        <td><strong>Họ và tên:</strong></td>
                        <td>${cert.resident_name}</td>
                    </tr>
                    <tr>
                        <td><strong>Số CCCD/CMND:</strong></td>
                        <td>${cert.resident_cid}</td>
                    </tr>
                    <tr>
                        <td><strong>Ngày sinh:</strong></td>
                        <td>${formatDate(cert.resident_dob)}</td>
                    </tr>
                </table>
                <p style="margin-top: 20px;">Được phép tạm vắng:</p>
                <table class="certificate-info">
                    <tr>
                        <td><strong>Từ ngày:</strong></td>
                        <td>${formatDate(cert.start_date)}</td>
                    </tr>
                    <tr>
                        <td><strong>Đến ngày:</strong></td>
                        <td>${formatDate(cert.end_date)}</td>
                    </tr>
                    <tr>
                        <td><strong>Nơi đến:</strong></td>
                        <td>${cert.destination}</td>
                    </tr>
                    <tr>
                        <td><strong>Lý do:</strong></td>
                        <td>${cert.reason}</td>
                    </tr>
                </table>
            </div>
            <div class="certificate-footer" style="margin-top: 40px; text-align: right; padding-right: 50px;">
                <p><em>Ngày cấp: ${formatDate(cert.issue_date)}</em></p>
                <p><strong>CÁN BỘ PHỤ TRÁCH</strong></p>
                <p style="margin-top: 60px;"><em>(Ký, ghi rõ họ tên)</em></p>
            </div>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn-secondary" onclick="closeModal()">Đóng</button>
            <button type="button" class="btn-add" onclick="printCertificate()">🖨️ In giấy</button>
        </div>
    `;

    showModal('Giấy xác nhận tạm vắng', modalContent);
}

function printCertificate() {
    const printContent = document.getElementById('certificate-print-area');
    if (!printContent) return;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Giấy xác nhận tạm vắng</title>
            <style>
                body {
                    font-family: 'Times New Roman', serif;
                    margin: 0;
                    padding: 40px;
                }
                .certificate-container {
                    max-width: 800px;
                    margin: 0 auto;
                }
                .certificate-header { text-align: center; }
                .certificate-header h2 { margin: 0; font-size: 16px; }
                .certificate-header p { margin: 5px 0; }
                .certificate-title { text-align: center; margin: 30px 0; }
                .certificate-title h1 { font-size: 22px; text-transform: uppercase; }
                .certificate-info { width: 100%; border-collapse: collapse; }
                .certificate-info td { padding: 8px 0; }
                .certificate-info td:first-child { width: 180px; }
                .certificate-footer { text-align: right; padding-right: 50px; }
            </style>
        </head>
        <body>
            ${printContent.innerHTML}
        </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
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
        const tbody = document.querySelector('#temp-res-table tbody');
        if (tbody) tbody.innerHTML = `
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
    const tbody = document.querySelector('#temp-res-table tbody');
    if (!tbody) return; // Guard against missing element

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

    try {
        showLoading();
        await apiCall(`/temp-residences/${id}/reject`, {
            method: 'POST',
            body: JSON.stringify({})
        });
        showToast('Đã từ chối đăng ký', 'success');
        loadTempResidences();
    } catch (error) {
        console.error('Error rejecting residence:', error);
    } finally {
        hideLoading();
    }
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
    if (modalId) {
        // Close specific static modal by ID (just hide it)
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    } else {
        // Close dynamic modal (remove it)
        const overlay = document.querySelector('.modal-overlay');
        if (overlay) {
            overlay.remove();
        }
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

        // Save token and role
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', username);
        localStorage.setItem('role', data.role);  // Save role from API response

        // Parse token to get user info
        const payload = parseJwt(data.access_token);
        State.token = data.access_token;
        State.user = { username, ...payload };
        State.role = data.role;  // Set role from API response

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
            c.status === 'PROCESSING' ? 'badge badge-warning' : 'badge badge-danger';
        const statusText = c.status === 'RESOLVED' ? 'Đã giải quyết' :
            c.status === 'PROCESSING' ? 'Đang xử lý' : 'Mới';

        // Get reporter name from reporter_list
        let reporterName = 'Không rõ';
        if (c.reporter_list && c.reporter_list.length > 0) {
            reporterName = c.reporter_list[0].username || 'Cư dân';
            if (c.reporter_list.length > 1) {
                reporterName += ` (+${c.reporter_list.length - 1})`;
            }
        }

        // Truncate content
        const contentPreview = (c.content || '').length > 80 ?
            c.content.substring(0, 80) + '...' : c.content;

        let actions = `
            <button class="icon-btn" onclick="viewComplaintDetails(${c.id})" title="Xem chi tiết">
                👁️
            </button>
        `;

        if (State.user && (State.user.role === 'admin' || State.user.role === 'leader')) {
            if (c.status !== 'RESOLVED') {
                actions += `
                    <button class="icon-btn" onclick="updateComplaintStatus(${c.id}, 'PROCESSING')" title="Đang xử lý" style="color: var(--warning);">
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
                <div style="font-weight: 600;">${reporterName}</div>
            </td>
            <td>
                <div style="color: var(--text-secondary); font-size: 13px;">${contentPreview}</div>
            </td>
            <td><span class="badge badge-info">${categoryMap[c.category] || c.category}</span></td>
            <td style="color: var(--text-secondary);">${formatDate(c.created_at)}</td>
            <td>
                <span class="${statusClass}">${statusText}</span>
                ${c.satisfaction_rating ? `<span style="color: #f59e0b; margin-left: 4px;">${'⭐'.repeat(c.satisfaction_rating)}</span>` : ''}
            </td>
            <td class="text-right">
                <div class="action-icons">
                    ${actions}
                    ${c.status === 'RESOLVED' && !c.satisfaction_rating && isUserReporter(c) ? `
                        <button class="icon-btn" onclick="showRatingModal(${c.id})" title="Đánh giá hài lòng" style="color: #f59e0b;">
                            ⭐
                        </button>
                    ` : ''}
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

// Check if current user is a reporter of the complaint
function isUserReporter(complaint) {
    if (!State.user) return false;

    if (complaint.reporter_id === State.user.user_id) return true;

    if (complaint.reporter_list) {
        for (const r of complaint.reporter_list) {
            if (r.user_id === State.user.user_id) return true;
        }
    }
    return false;
}

// Show rating modal
function showRatingModal(complaintId) {
    const content = `
        <form id="rating-form" style="text-align: center;">
            <p style="margin-bottom: 16px; color: #64748b;">Bạn hài lòng với việc xử lý phản ánh này như thế nào?</p>
            
            <div style="font-size: 32px; margin-bottom: 16px;" id="star-rating">
                ${[1, 2, 3, 4, 5].map(i => `
                    <span class="star" data-rating="${i}" onclick="selectRating(${i})" 
                          style="cursor: pointer; color: #e2e8f0; transition: color 0.2s;">⭐</span>
                `).join('')}
            </div>
            <input type="hidden" id="rating-value" value="0">
            
            <div style="margin-bottom: 16px;">
                <textarea id="rating-comment" class="form-control" rows="3" 
                    placeholder="Nhận xét thêm (tùy chọn)..." style="width: 100%;"></textarea>
            </div>
            
            <button type="submit" class="btn-primary" onclick="submitRating(${complaintId}); return false;" 
                style="width: 100%;">
                Gửi đánh giá
            </button>
        </form>
    `;
    showModal('⭐ Đánh giá mức độ hài lòng', content);
}

function selectRating(rating) {
    document.getElementById('rating-value').value = rating;
    const stars = document.querySelectorAll('#star-rating .star');
    stars.forEach((star, index) => {
        star.style.color = index < rating ? '#f59e0b' : '#e2e8f0';
    });
}

async function submitRating(complaintId) {
    const rating = parseInt(document.getElementById('rating-value').value);
    const comment = document.getElementById('rating-comment').value;

    if (rating < 1 || rating > 5) {
        showToast('Vui lòng chọn số sao đánh giá', 'error');
        return;
    }

    try {
        const result = await apiCall(`/complaints/${complaintId}/rate`, {
            method: 'POST',
            body: JSON.stringify({ rating, comment })
        });
        if (result) {
            showToast(result.message || 'Đánh giá thành công!', 'success');
            closeModal(); // Close dynamic modal
            loadComplaints(); // Reload to show rating
        }
    } catch (error) {
        showToast('Có lỗi xảy ra: ' + error.message, 'error');
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
        complaint.status === 'PROCESSING' ? 'Đang xử lý' : 'Mới';

    const statusClass = complaint.status === 'RESOLVED' ? 'status-approved' :
        complaint.status === 'PROCESSING' ? 'status-pending' : 'badge-danger';

    // Build reporter list HTML
    let reportersHtml = '';
    if (complaint.reporter_list && complaint.reporter_list.length > 0) {
        reportersHtml = `
            <div style="margin-bottom: 16px;">
                <strong>👥 Danh sách người phản ánh (${complaint.reporter_list.length}):</strong>
                <div style="padding: 12px; background: #fff8e1; border-radius: 6px; margin-top: 8px; max-height: 150px; overflow-y: auto;">
                    ${complaint.reporter_list.map((r, i) => `
                        <div style="padding: 6px 0; ${i > 0 ? 'border-top: 1px solid #ffe082;' : ''}">
                            <span style="font-weight: 500;">${r.username}</span>
                            <span style="color: #666; font-size: 12px; margin-left: 8px;">${formatDate(r.at)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Respond button for leaders/admins
    let respondButton = '';
    if (State.user && (State.user.role === 'admin' || State.user.role === 'leader') && complaint.status !== 'RESOLVED') {
        respondButton = `
            <button type="button" class="btn-primary" onclick="showRespondForm(${id})" style="margin-right: 8px;">
                📝 Thêm phản hồi từ cấp trên
            </button>
        `;
    }

    showModal('Chi tiết phản ánh', `
        <div>
            <div style="margin-bottom: 16px;">
                <strong>Danh mục:</strong> ${categoryMap[complaint.category]}
            </div>
            <div style="margin-bottom: 16px;">
                <strong>Trạng thái:</strong> <span class="status-badge ${statusClass}">${statusText}</span>
            </div>
            <div style="margin-bottom: 16px;">
                <strong>Ngày tạo:</strong> ${formatDate(complaint.created_at)}
            </div>
            ${complaint.duplication_count > 0 ? `
                <div style="margin-bottom: 16px;">
                    <strong>Số lượng phản ánh tương tự:</strong> <span class="impact-badge">${complaint.duplication_count + 1} Reports</span>
                </div>
            ` : ''}
            ${reportersHtml}
            <div style="margin-bottom: 16px;">
                <strong>Nội dung:</strong>
                <div style="padding: 12px; background: #f5f5f5; border-radius: 6px; margin-top: 8px;">
                    ${complaint.content}
                </div>
            </div>
            ${complaint.resolution_note ? `
                <div style="margin-bottom: 16px;">
                    <strong>📋 Phản hồi/Ghi chú giải quyết:</strong>
                    <div style="padding: 12px; background: #e8f5e9; border-radius: 6px; margin-top: 8px;">
                        ${complaint.resolution_note}
                    </div>
                </div>
            ` : ''}
        </div>
        <div class="modal-footer">
            ${respondButton}
            <button type="button" class="btn-secondary" onclick="closeModal()">Đóng</button>
        </div>
    `);
}

// Show form for leader to add response from upper management
function showRespondForm(complaintId) {
    closeModal();

    showModal('Thêm phản hồi từ cấp trên', `
        <form id="respond-form" onsubmit="handleRespondComplaint(event, ${complaintId})">
            <div class="form-group">
                <label for="response-content">Nội dung phản hồi *</label>
                <textarea id="response-content" rows="4" required placeholder="Nhập phản hồi từ cấp trên..."></textarea>
            </div>
            <div class="form-group">
                <label for="response-status">Cập nhật trạng thái</label>
                <select id="response-status">
                    <option value="PROCESSING">Đang xử lý</option>
                    <option value="RESOLVED">Đã giải quyết</option>
                </select>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Gửi phản hồi</button>
            </div>
        </form>
    `);
}

// Handle response submission
async function handleRespondComplaint(event, complaintId) {
    event.preventDefault();

    const responseContent = document.getElementById('response-content').value;
    const newStatus = document.getElementById('response-status').value;

    try {
        showLoading();
        const result = await apiCall(`/complaints/${complaintId}/respond`, {
            method: 'POST',
            body: JSON.stringify({
                response_content: responseContent,
                new_status: newStatus
            })
        });

        if (result && result.status === 'success') {
            const reporterCount = result.reporters_to_notify?.length || 0;
            showToast(`Đã thêm phản hồi. ${reporterCount} người sẽ được thông báo.`, 'success');
            closeModal();
            loadComplaints();
        }
    } catch (error) {
        console.error('Error responding to complaint:', error);
        showToast('Có lỗi xảy ra', 'error');
    } finally {
        hideLoading();
    }
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

        // Initialize year filter if not done
        initYearFilter();

        const selectedYear = document.getElementById('stats-year-filter')?.value || new Date().getFullYear();

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

                // Update summary boxes
                updateGenderSummary(popStats.gender_distribution);
                updateAgeSummary(popStats.age_distribution);
            }
        } catch (e) {
            console.log('Population stats not available:', e.message);
        }

        // Load temp status details
        try {
            const tempStatus = await apiCall('/stats/temp-status');
            if (tempStatus) {
                // Update absent cards
                document.getElementById('absent-pending').textContent = tempStatus.absent?.pending || 0;
                document.getElementById('absent-approved').textContent = tempStatus.absent?.approved || 0;
                document.getElementById('absent-active').textContent = tempStatus.absent?.active_today || 0;

                // Update temp residence cards
                document.getElementById('tempres-pending').textContent = tempStatus.temp_residence?.pending || 0;
                document.getElementById('tempres-approved').textContent = tempStatus.temp_residence?.approved || 0;
                document.getElementById('tempres-active').textContent = tempStatus.temp_residence?.active_today || 0;
            }
        } catch (e) {
            console.log('Temp status stats not available:', e.message);
        }

        // Load complaints stats with year filter
        try {
            const complaintStats = await apiCall(`/stats/complaints-quarterly?year=${selectedYear}`);
            if (complaintStats) {
                renderComplaintsChart(complaintStats);
            }
        } catch (e) {
            console.log('Complaint stats not available:', e.message);
        }

        // Load admin-only advanced statistics
        await loadAdminStatistics();

    } catch (error) {
        console.error('Error loading statistics:', error);
    } finally {
        hideLoading();
    }
}

function initYearFilter() {
    const select = document.getElementById('stats-year-filter');
    if (!select || select.options.length > 0) return;

    const currentYear = new Date().getFullYear();
    for (let year = currentYear; year >= currentYear - 5; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        select.appendChild(option);
    }
}

function updateGenderSummary(data) {
    const container = document.getElementById('gender-stats-summary');
    if (!container) return;

    const male = data?.MALE || 0;
    const female = data?.FEMALE || 0;
    const total = male + female;
    const malePercent = total > 0 ? ((male / total) * 100).toFixed(1) : 0;
    const femalePercent = total > 0 ? ((female / total) * 100).toFixed(1) : 0;

    container.innerHTML = `
        <div style="display: flex; justify-content: space-between;">
            <span>👨 Nam: <strong>${male}</strong> (${malePercent}%)</span>
            <span>👩 Nữ: <strong>${female}</strong> (${femalePercent}%)</span>
            <span>📊 Tổng: <strong>${total}</strong></span>
        </div>
    `;
}

function updateAgeSummary(data) {
    const container = document.getElementById('age-stats-summary');
    if (!container) return;

    const child = data?.['0-14'] || 0;
    const adult = data?.['15-59'] || 0;
    const senior = data?.['60+'] || 0;
    const total = child + adult + senior;

    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
            <span>👶 Trẻ em (0-14): <strong>${child}</strong></span>
            <span>👨‍💼 Lao động (15-59): <strong>${adult}</strong></span>
            <span>👴 Cao tuổi (60+): <strong>${senior}</strong></span>
        </div>
    `;
}

function exportStatistics() {
    // Generate CSV export
    const data = {
        generated_at: new Date().toISOString(),
        summary: {
            total_households: document.getElementById('total-households')?.textContent || 0,
            total_persons: document.getElementById('total-persons')?.textContent || 0,
            absent_and_temp: document.getElementById('total-absent')?.textContent || '0 / 0',
            pending_complaints: document.getElementById('total-complaints')?.textContent || 0
        },
        temp_status: {
            absent_pending: document.getElementById('absent-pending')?.textContent || 0,
            absent_approved: document.getElementById('absent-approved')?.textContent || 0,
            absent_active: document.getElementById('absent-active')?.textContent || 0,
            tempres_pending: document.getElementById('tempres-pending')?.textContent || 0,
            tempres_approved: document.getElementById('tempres-approved')?.textContent || 0,
            tempres_active: document.getElementById('tempres-active')?.textContent || 0
        }
    };

    // Create CSV content
    let csv = 'Báo cáo thống kê nhân khẩu\n';
    csv += `Ngày xuất: ${formatDate(new Date().toISOString())}\n\n`;
    csv += 'Chỉ tiêu,Giá trị\n';
    csv += `Tổng hộ khẩu,${data.summary.total_households}\n`;
    csv += `Tổng nhân khẩu,${data.summary.total_persons}\n`;
    csv += `Tạm vắng / Tạm trú,${data.summary.absent_and_temp}\n`;
    csv += `Phản ánh chờ xử lý,${data.summary.pending_complaints}\n\n`;
    csv += 'Chi tiết tạm vắng:\n';
    csv += `Chờ duyệt,${data.temp_status.absent_pending}\n`;
    csv += `Đã duyệt,${data.temp_status.absent_approved}\n`;
    csv += `Đang vắng,${data.temp_status.absent_active}\n\n`;
    csv += 'Chi tiết tạm trú:\n';
    csv += `Chờ duyệt,${data.temp_status.tempres_pending}\n`;
    csv += `Đã duyệt,${data.temp_status.tempres_approved}\n`;
    csv += `Đang trú,${data.temp_status.tempres_active}\n`;

    // Download CSV
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `thong_ke_nhan_khau_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();

    showToast('Đã xuất báo cáo thành công', 'success');
}

function printStatistics() {
    const statsSection = document.getElementById('tab-statistics');
    if (!statsSection) return;

    // Create print window
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Báo cáo thống kê nhân khẩu - ${formatDate(new Date().toISOString())}</title>
            <style>
                body { font-family: 'Inter', 'Roboto', sans-serif; padding: 20px; }
                h1 { text-align: center; color: #1e3a5f; }
                .kpi-row { display: flex; gap: 16px; flex-wrap: wrap; margin: 20px 0; }
                .kpi-card { background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; flex: 1; min-width: 200px; }
                .kpi-label { font-size: 12px; color: #64748b; }
                .kpi-value { font-size: 24px; font-weight: 700; color: #1e40af; }
                .print-date { text-align: center; color: #64748b; margin-bottom: 20px; }
                @media print { body { print-color-adjust: exact; -webkit-print-color-adjust: exact; } }
            </style>
        </head>
        <body>
            <h1>🏢 BÁO CÁO THỐNG KÊ NHÂN KHẨU</h1>
            <div class="print-date">Ngày in: ${formatDate(new Date().toISOString())}</div>
            
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-label">Tổng nhân khẩu</div>
                    <div class="kpi-value">${document.getElementById('total-persons')?.textContent || 0}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Hộ gia đình</div>
                    <div class="kpi-value">${document.getElementById('total-households')?.textContent || 0}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Tạm vắng / Tạm trú</div>
                    <div class="kpi-value">${document.getElementById('total-absent')?.textContent || '0 / 0'}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Phản ánh chờ xử lý</div>
                    <div class="kpi-value">${document.getElementById('total-complaints')?.textContent || 0}</div>
                </div>
            </div>
            
            <h2>Chi tiết Tạm vắng</h2>
            <div class="kpi-row">
                <div class="kpi-card"><div class="kpi-label">Chờ duyệt</div><div class="kpi-value">${document.getElementById('absent-pending')?.textContent || 0}</div></div>
                <div class="kpi-card"><div class="kpi-label">Đã duyệt</div><div class="kpi-value">${document.getElementById('absent-approved')?.textContent || 0}</div></div>
                <div class="kpi-card"><div class="kpi-label">Đang vắng</div><div class="kpi-value">${document.getElementById('absent-active')?.textContent || 0}</div></div>
            </div>
            
            <h2>Chi tiết Tạm trú</h2>
            <div class="kpi-row">
                <div class="kpi-card"><div class="kpi-label">Chờ duyệt</div><div class="kpi-value">${document.getElementById('tempres-pending')?.textContent || 0}</div></div>
                <div class="kpi-card"><div class="kpi-label">Đã duyệt</div><div class="kpi-value">${document.getElementById('tempres-approved')?.textContent || 0}</div></div>
                <div class="kpi-card"><div class="kpi-label">Đang trú</div><div class="kpi-value">${document.getElementById('tempres-active')?.textContent || 0}</div></div>
            </div>
            
            <h2>Thống kê độ tuổi</h2>
            <div id="age-summary">${document.getElementById('age-stats-summary')?.innerHTML || ''}</div>
            
            <h2>Thống kê giới tính</h2>
            <div id="gender-summary">${document.getElementById('gender-stats-summary')?.innerHTML || ''}</div>
        </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
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

// ==========================================
// ADMIN ADVANCED STATISTICS
// ==========================================

let householdSizeChart = null;
let residentStatusChart = null;
let residentRelationChart = null;
let complaintsCategoryChart = null;
let changeHistoryChart = null;

// Switch between admin stats tabs
function switchAdminTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.admin-tab').forEach(btn => {
        if (btn.dataset.tab === tabName) {
            btn.style.background = 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)';
            btn.style.color = 'white';
        } else {
            btn.style.background = 'white';
            btn.style.color = '#475569';
        }
    });

    // Show/hide tab content
    document.querySelectorAll('.admin-tab-content').forEach(content => {
        content.style.display = 'none';
    });
    const activeContent = document.getElementById('admin-tab-' + tabName);
    if (activeContent) {
        activeContent.style.display = 'block';
    }

    // Load data for the tab if needed
    loadAdminTabData(tabName);
}

async function loadAdminTabData(tabName) {
    const selectedYear = document.getElementById('stats-year-filter')?.value || new Date().getFullYear();

    try {
        if (tabName === 'household-size') {
            await loadHouseholdSizeStats();
            await loadAdvancedSummary();
        } else if (tabName === 'resident-status') {
            await loadResidentStatusStats();
        } else if (tabName === 'resident-relation') {
            await loadResidentRelationStats();
        } else if (tabName === 'complaints-category') {
            await loadComplaintsCategoryStats(selectedYear);
            await loadComplaintsResolutionStats(selectedYear);
        } else if (tabName === 'change-history') {
            await loadChangeHistoryStats(selectedYear);
        }
    } catch (error) {
        console.error('Error loading admin tab data:', error);
    }
}

// Load admin statistics if user is admin
async function loadAdminStatistics() {
    if (State.role !== 'admin') {
        const section = document.getElementById('admin-stats-section');
        if (section) section.style.display = 'none';
        return;
    }

    // Show admin section
    const section = document.getElementById('admin-stats-section');
    if (section) section.style.display = 'block';

    // Load default tab data
    await loadAdminTabData('household-size');
}

async function loadHouseholdSizeStats() {
    try {
        const data = await apiCall('/admin-stats/household-size');
        if (data) {
            renderHouseholdSizeChart(data);
        }
    } catch (e) {
        console.log('Household size stats not available:', e.message);
    }
}

function renderHouseholdSizeChart(data) {
    const ctx = document.getElementById('household-size-chart')?.getContext('2d');
    if (!ctx) return;

    if (householdSizeChart) {
        householdSizeChart.destroy();
    }

    const labels = Object.keys(data.distribution);
    const values = Object.values(data.distribution);
    const colors = ['#3b82f6', '#10b981', '#f59e0b'];

    householdSizeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // Update summary
    const summaryEl = document.getElementById('household-size-summary');
    if (summaryEl) {
        const total = values.reduce((a, b) => a + b, 0);
        summaryEl.innerHTML = `
            <strong>Tổng số hộ đã thống kê:</strong> ${total} hộ<br>
            <strong>Hộ chưa có thành viên:</strong> ${data.empty_households || 0} hộ
        `;
    }
}

async function loadAdvancedSummary() {
    try {
        const data = await apiCall('/admin-stats/summary-advanced');
        if (data) {
            document.getElementById('avg-household-size').textContent = data.average_household_size || 0;
            document.getElementById('gender-ratio-display').textContent = data.gender_ratio || 0;

            // Top households
            const listEl = document.getElementById('top-households-list');
            if (listEl && data.top_households) {
                listEl.innerHTML = data.top_households.map((h, i) => `
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #e2e8f0;">
                        <span>${i + 1}. ${h.code}</span>
                        <span style="font-weight: 600; color: #3b82f6;">${h.members} người</span>
                    </div>
                `).join('');
            }
        }
    } catch (e) {
        console.log('Advanced summary not available:', e.message);
    }
}

async function loadResidentStatusStats() {
    try {
        const data = await apiCall('/admin-stats/resident-status');
        if (data) {
            renderResidentStatusChart(data);
        }
    } catch (e) {
        console.log('Resident status stats not available:', e.message);
    }
}

function renderResidentStatusChart(data) {
    const ctx = document.getElementById('resident-status-chart')?.getContext('2d');
    if (!ctx) return;

    if (residentStatusChart) {
        residentStatusChart.destroy();
    }

    const labels = Object.keys(data.distribution);
    const values = Object.values(data.distribution);
    const colors = ['#10b981', '#f59e0b', '#3b82f6', '#ef4444'];

    residentStatusChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

async function loadResidentRelationStats() {
    try {
        const data = await apiCall('/admin-stats/resident-relation');
        if (data) {
            renderResidentRelationChart(data);
        }
    } catch (e) {
        console.log('Resident relation stats not available:', e.message);
    }
}

function renderResidentRelationChart(data) {
    const ctx = document.getElementById('resident-relation-chart')?.getContext('2d');
    if (!ctx) return;

    if (residentRelationChart) {
        residentRelationChart.destroy();
    }

    const labels = Object.keys(data.distribution);
    const values = Object.values(data.distribution);
    const colors = ['#3b82f6', '#ec4899', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#6366f1', '#14b8a6'];

    residentRelationChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Số lượng',
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

async function loadComplaintsCategoryStats(year) {
    try {
        const data = await apiCall(`/admin-stats/complaints-category?year=${year}`);
        if (data) {
            renderComplaintsCategoryChart(data);
        }
    } catch (e) {
        console.log('Complaints category stats not available:', e.message);
    }
}

function renderComplaintsCategoryChart(data) {
    const ctx = document.getElementById('complaints-category-chart')?.getContext('2d');
    if (!ctx) return;

    if (complaintsCategoryChart) {
        complaintsCategoryChart.destroy();
    }

    const labels = Object.keys(data.distribution);
    const values = Object.values(data.distribution);
    const colors = ['#ef4444', '#10b981', '#3b82f6'];

    complaintsCategoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

async function loadComplaintsResolutionStats(year) {
    try {
        const data = await apiCall(`/admin-stats/complaints-resolution?year=${year}`);
        if (data) {
            document.getElementById('resolution-rate').textContent = `${data.resolution_rate}%`;
            document.getElementById('new-complaints-count').textContent = data.new || 0;
            document.getElementById('processing-complaints-count').textContent = data.processing || 0;
            document.getElementById('resolved-complaints-count').textContent = data.resolved || 0;
        }
    } catch (e) {
        console.log('Complaints resolution stats not available:', e.message);
    }
}

async function loadChangeHistoryStats(year) {
    try {
        const data = await apiCall(`/admin-stats/change-history?year=${year}`);
        if (data) {
            renderChangeHistoryChart(data);
        }
    } catch (e) {
        console.log('Change history stats not available:', e.message);
    }
}

function renderChangeHistoryChart(data) {
    const ctx = document.getElementById('change-history-chart')?.getContext('2d');
    if (!ctx) return;

    if (changeHistoryChart) {
        changeHistoryChart.destroy();
    }

    const labels = Object.keys(data.by_type);
    const values = Object.values(data.by_type);
    const colors = ['#f59e0b', '#10b981', '#ef4444'];

    changeHistoryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Số lượng',
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });

    // Update summary
    const summaryEl = document.getElementById('change-history-summary');
    if (summaryEl) {
        summaryEl.innerHTML = `
            <strong>Năm ${data.year}:</strong> Tổng ${data.total || 0} thay đổi<br>
            ${Object.entries(data.by_type).map(([k, v]) => `<span style="margin-right: 16px;">${k}: <strong>${v}</strong></span>`).join('')}
        `;
    }
}

// ==========================================
// GLOBAL SEARCH
// ==========================================

let searchTimeout = null;

function initGlobalSearch() {
    const searchInput = document.getElementById('global-search');
    if (!searchInput) return;

    // Create search results dropdown
    let dropdown = document.getElementById('search-results-dropdown');
    if (!dropdown) {
        dropdown = document.createElement('div');
        dropdown.id = 'search-results-dropdown';
        dropdown.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        `;
        searchInput.parentElement.style.position = 'relative';
        searchInput.parentElement.appendChild(dropdown);
    }

    // Add event listener
    searchInput.addEventListener('input', function () {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }

        searchTimeout = setTimeout(() => {
            performGlobalSearch(query);
        }, 300);
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

async function performGlobalSearch(query) {
    const dropdown = document.getElementById('search-results-dropdown');
    if (!dropdown) return;

    try {
        const results = await apiCall(`/stats/search?q=${encodeURIComponent(query)}`);

        if (!results || (results.persons.length === 0 && results.households.length === 0)) {
            dropdown.innerHTML = '<div style="padding: 16px; color: #64748b; text-align: center;">Không tìm thấy kết quả</div>';
            dropdown.style.display = 'block';
            return;
        }

        let html = '';

        if (results.persons.length > 0) {
            html += '<div style="padding: 8px 16px; background: #f1f5f9; font-weight: 600; color: #475569;">👤 Nhân khẩu</div>';
            results.persons.forEach(p => {
                html += `
                    <div class="search-result-item" style="padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #f1f5f9;" 
                         onclick="viewPersonFromSearch(${p.id})" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='white'">
                        <div style="font-weight: 500;">${p.full_name}</div>
                        <div style="font-size: 12px; color: #64748b;">CCCD: ${p.cid}</div>
                    </div>
                `;
            });
        }

        if (results.households.length > 0) {
            html += '<div style="padding: 8px 16px; background: #f1f5f9; font-weight: 600; color: #475569;">🏠 Hộ khẩu</div>';
            results.households.forEach(h => {
                html += `
                    <div class="search-result-item" style="padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #f1f5f9;" 
                         onclick="viewHouseholdFromSearch(${h.id})" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='white'">
                        <div style="font-weight: 500;">${h.household_code}</div>
                        <div style="font-size: 12px; color: #64748b;">${h.address}</div>
                    </div>
                `;
            });
        }

        dropdown.innerHTML = html;
        dropdown.style.display = 'block';
    } catch (error) {
        console.error('Search error:', error);
        dropdown.style.display = 'none';
    }
}

function viewPersonFromSearch(id) {
    document.getElementById('search-results-dropdown').style.display = 'none';
    document.getElementById('global-search').value = '';
    switchTab('persons');
    // Highlight person after a small delay
    setTimeout(() => {
        const row = document.querySelector(`#persons-table tr[data-id="${id}"]`);
        if (row) {
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            row.style.background = '#fef3c7';
            setTimeout(() => { row.style.background = ''; }, 2000);
        }
    }, 500);
}

function viewHouseholdFromSearch(id) {
    document.getElementById('search-results-dropdown').style.display = 'none';
    document.getElementById('global-search').value = '';
    switchTab('households');
    viewHouseholdHistory(id);
}

// ==========================================
// HOUSEHOLD HISTORY
// ==========================================

async function viewHouseholdHistory(id) {
    try {
        showLoading();
        const data = await apiCall(`/households/${id}/history`);

        if (!data) {
            showToast('Không thể tải lịch sử hộ khẩu', 'error');
            return;
        }

        const changeTypeLabels = {
            'MOVED_IN': '📥 Nhập khẩu',
            'MOVED_OUT': '📤 Chuyển đi',
            'SPLIT': '✂️ Tách khẩu',
            'MERGE': '🔗 Nhập chung',
            'UPDATE': '✏️ Cập nhật',
            'CREATED': '➕ Tạo mới'
        };

        let historyHtml = '';

        if (!data.history || data.history.length === 0) {
            historyHtml = `
                <div style="text-align: center; padding: 40px; color: #64748b;">
                    <div style="font-size: 48px; margin-bottom: 8px;">📜</div>
                    <p>Chưa có lịch sử thay đổi</p>
                </div>
            `;
        } else {
            historyHtml = data.history.map(h => `
                <div style="border-left: 3px solid var(--accent-color); padding: 12px 16px; margin-bottom: 12px; background: #f8fafc; border-radius: 0 8px 8px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span class="badge badge-info">${changeTypeLabels[h.change_type] || h.change_type}</span>
                        <span style="font-size: 12px; color: #64748b;">${formatDate(h.created_at)}</span>
                    </div>
                    <div style="font-weight: 500; margin-bottom: 4px;">👤 ${h.resident_name}</div>
                    <div style="font-size: 13px; color: #475569;">
                        ${h.old_data ? 'Từ: ' + JSON.stringify(h.old_data) : ''}
                        ${h.new_data ? ' → ' + JSON.stringify(h.new_data) : ''}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Thực hiện bởi: ${h.changed_by}</div>
                </div>
            `).join('');
        }

        showModal(`📜 Lịch sử hộ khẩu ${data.household_code}`, `
            <div style="max-height: 400px; overflow-y: auto;">
                ${historyHtml}
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Đóng</button>
            </div>
        `);
    } catch (error) {
        console.error('Error loading household history:', error);
        showToast('Không thể tải lịch sử', 'error');
    } finally {
        hideLoading();
    }
}

// Initialize global search on page load
document.addEventListener('DOMContentLoaded', () => {
    initGlobalSearch();
});

// ==========================================
// Q&A SYSTEM
// ==========================================

let questionsData = [];

async function loadQuestions() {
    try {
        showLoading();
        const targetFilter = document.getElementById('question-target-filter')?.value || '';
        const statusFilter = document.getElementById('question-status-filter')?.value || '';

        let url = '/questions';
        const params = new URLSearchParams();
        if (targetFilter) params.append('target_role', targetFilter);
        if (statusFilter) params.append('status', statusFilter);

        // For residents, show their own questions; for leaders/admins show questions to them
        if (State.role === 'resident') {
            params.append('my_questions', 'true');
        }

        if (params.toString()) url += '?' + params.toString();

        const questions = await apiCall(url);
        if (questions) {
            questionsData = questions;
            renderQuestionsTable(questions);
        }
    } catch (error) {
        console.error('Error loading questions:', error);
        showToast('Không thể tải danh sách câu hỏi', 'error');
    } finally {
        hideLoading();
    }
}

function renderQuestionsTable(questions) {
    const tbody = document.querySelector('#questions-table tbody');
    if (!tbody) return;

    if (!questions || questions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">❓</div>
                    <p>Chưa có câu hỏi nào</p>
                    <button class="btn-primary" onclick="showAskQuestionModal()" style="margin-top: 12px;">
                        Đặt câu hỏi đầu tiên
                    </button>
                </td>
            </tr>
        `;
        return;
    }

    const statusLabels = {
        'PENDING': '<span class="badge badge-warning">Chờ trả lời</span>',
        'ANSWERED': '<span class="badge badge-success">Đã trả lời</span>',
        'CLOSED': '<span class="badge badge-secondary">Đã đóng</span>'
    };

    const targetLabels = {
        'leader': '👨‍💼 Tổ trưởng',
        'admin': '👨‍💻 Admin'
    };

    tbody.innerHTML = questions.map(q => `
        <tr>
            <td><strong>${q.asker_username || 'N/A'}</strong></td>
            <td>
                <a href="#" onclick="viewQuestionDetail(${q.id})" style="color: var(--accent-color); text-decoration: none;">
                    ${q.title}
                </a>
            </td>
            <td>${targetLabels[q.target_role] || q.target_role}</td>
            <td>${formatDate(q.created_at)}</td>
            <td>${q.answer_count || 0}</td>
            <td>${statusLabels[q.status] || q.status}</td>
            <td class="text-right">
                <div class="action-icons">
                    <button class="icon-btn" onclick="viewQuestionDetail(${q.id})" title="Xem chi tiết">👁️</button>
                    ${q.status !== 'CLOSED' && (q.asker_id === State.user?.user_id || State.role === 'admin') ?
            `<button class="icon-btn" onclick="closeQuestion(${q.id})" title="Đóng câu hỏi">✓</button>` : ''
        }
                </div>
            </td>
        </tr>
    `).join('');
}

function filterQuestions() {
    loadQuestions();
}

function showAskQuestionModal() {
    const modal = document.getElementById('ask-question-modal');
    if (modal) {
        modal.style.display = 'flex';
        // Clear form
        document.getElementById('question-title').value = '';
        document.getElementById('question-content').value = '';
        document.getElementById('question-target').value = 'leader';
    }
}

async function submitQuestion() {
    const title = document.getElementById('question-title').value.trim();
    const content = document.getElementById('question-content').value.trim();
    const targetRole = document.getElementById('question-target').value;

    if (!title || !content) {
        showToast('Vui lòng điền đầy đủ tiêu đề và nội dung', 'error');
        return;
    }

    try {
        showLoading();
        const result = await apiCall('/questions/', {
            method: 'POST',
            body: JSON.stringify({
                title: title,
                content: content,
                target_role: targetRole
            })
        });

        if (result) {
            showToast('Câu hỏi đã được gửi thành công!', 'success');
            closeModal('ask-question-modal');
            loadQuestions();
        }
    } catch (error) {
        console.error('Error submitting question:', error);
        showToast('Không thể gửi câu hỏi', 'error');
    } finally {
        hideLoading();
    }
}

async function viewQuestionDetail(questionId) {
    try {
        showLoading();
        const question = await apiCall(`/questions/${questionId}`);

        if (!question) {
            showToast('Không tìm thấy câu hỏi', 'error');
            return;
        }

        document.getElementById('question-detail-title').textContent = '❓ ' + question.title;

        const statusLabels = {
            'PENDING': '<span class="badge badge-warning">Chờ trả lời</span>',
            'ANSWERED': '<span class="badge badge-success">Đã trả lời</span>',
            'CLOSED': '<span class="badge badge-secondary">Đã đóng</span>'
        };

        // Build answers HTML
        let answersHtml = '';
        if (question.answers && question.answers.length > 0) {
            answersHtml = question.answers.map(a => `
                <div style="background: #d1fae5; padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #10b981;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <strong style="color: #065f46;">💬 ${a.answerer_username}</strong>
                        <span style="font-size: 12px; color: #64748b;">${formatDate(a.created_at)}</span>
                    </div>
                    <p style="margin: 0; color: #1e293b;">${a.content}</p>
                </div>
            `).join('');
        } else {
            answersHtml = '<p style="color: #94a3b8; text-align: center; padding: 16px;">Chưa có câu trả lời</p>';
        }

        document.getElementById('question-detail-body').innerHTML = `
            <div style="background: #f8fafc; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="color: #64748b;">Người hỏi: <strong>${question.asker_username}</strong></span>
                    ${statusLabels[question.status] || question.status}
                </div>
                <p style="color: #1e293b; font-size: 15px; line-height: 1.6;">${question.content}</p>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 8px;">
                    📅 ${formatDate(question.created_at)}
                </div>
            </div>
            
            <h4 style="margin-bottom: 12px; color: #10b981;">📝 Câu trả lời (${question.answers?.length || 0})</h4>
            ${answersHtml}
        `;

        // Show answer form for leaders/admins if question is not closed
        const footerEl = document.getElementById('question-detail-footer');
        if ((State.role === 'leader' || State.role === 'admin') && question.status !== 'CLOSED') {
            footerEl.innerHTML = `
                <div style="width: 100%; margin-bottom: 12px;">
                    <textarea id="answer-content" class="form-control" rows="3" placeholder="Nhập câu trả lời của bạn..."></textarea>
                </div>
                <button class="btn-secondary" onclick="closeModal('question-detail-modal')">Đóng</button>
                <button class="btn-primary" onclick="submitAnswer(${questionId})">Gửi trả lời</button>
            `;
        } else {
            footerEl.innerHTML = `
                <button class="btn-secondary" onclick="closeModal('question-detail-modal')">Đóng</button>
            `;
        }

        document.getElementById('question-detail-modal').style.display = 'flex';

    } catch (error) {
        console.error('Error loading question detail:', error);
        showToast('Không thể tải chi tiết câu hỏi', 'error');
    } finally {
        hideLoading();
    }
}

async function submitAnswer(questionId) {
    const content = document.getElementById('answer-content').value.trim();

    if (!content) {
        showToast('Vui lòng nhập nội dung câu trả lời', 'error');
        return;
    }

    try {
        showLoading();
        const result = await apiCall(`/questions/${questionId}/answers`, {
            method: 'POST',
            body: JSON.stringify({ content: content })
        });

        if (result) {
            showToast('Đã gửi câu trả lời!', 'success');
            closeModal('question-detail-modal');
            loadQuestions();
        }
    } catch (error) {
        console.error('Error submitting answer:', error);
        showToast('Không thể gửi câu trả lời', 'error');
    } finally {
        hideLoading();
    }
}

async function closeQuestion(questionId) {
    if (!confirm('Bạn có chắc chắn muốn đóng câu hỏi này?')) {
        return;
    }

    try {
        showLoading();
        const result = await apiCall(`/questions/${questionId}/close`, { method: 'PUT' });

        if (result) {
            showToast('Đã đóng câu hỏi', 'success');
            loadQuestions();
        }
    } catch (error) {
        console.error('Error closing question:', error);
        showToast('Không thể đóng câu hỏi', 'error');
    } finally {
        hideLoading();
    }
}

// ==========================================
// REMINDERS SYSTEM
// ==========================================

let remindersData = [];

async function loadReminders() {
    // Show admin panel for admin/leader
    const adminPanel = document.getElementById('admin-reminders-panel');
    if (adminPanel) {
        adminPanel.style.display = (State.role === 'admin' || State.role === 'leader') ? 'flex' : 'none';
    }

    try {
        showLoading();
        const statusFilter = document.getElementById('reminder-status-filter')?.value || '';

        let url;
        if (State.role === 'admin' || State.role === 'leader') {
            url = '/reminders/admin/all';
            if (statusFilter) url += `?status=${statusFilter}`;
        } else {
            url = '/reminders/my';
        }

        const reminders = await apiCall(url);
        if (reminders) {
            remindersData = reminders;
            renderRemindersTable(reminders);
        }
    } catch (error) {
        console.error('Error loading reminders:', error);
        // Show empty state instead of error for new setup
        renderRemindersTable([]);
    } finally {
        hideLoading();
    }
}

function renderRemindersTable(reminders) {
    const tbody = document.querySelector('#reminders-table tbody');
    if (!tbody) return;

    if (!reminders || reminders.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center" style="padding: 40px;">
                    <div class="empty-state-icon">🔔</div>
                    <p>Chưa có nhắc nhở nào</p>
                    ${State.role === 'admin' ? `
                        <button class="btn-primary" onclick="generateReminders()" style="margin-top: 12px;">
                            🔄 Tạo nhắc nhở tự động
                        </button>
                    ` : ''}
                </td>
            </tr>
        `;
        return;
    }

    const statusLabels = {
        'PENDING': '<span class="badge badge-warning">Chờ xử lý</span>',
        'SENT': '<span class="badge badge-info">Đã gửi</span>',
        'ACKNOWLEDGED': '<span class="badge badge-success">Đã xem</span>',
        'DISMISSED': '<span class="badge badge-secondary">Bỏ qua</span>'
    };

    tbody.innerHTML = reminders.map(r => `
        <tr>
            <td><strong>${r.resident_name || 'N/A'}</strong></td>
            <td>${r.title}</td>
            <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis;">${r.message}</td>
            <td>${r.due_date ? formatDate(r.due_date) : '-'}</td>
            <td>${statusLabels[r.status] || r.status}</td>
            <td class="text-right">
                <div class="action-icons">
                    ${r.status === 'SENT' && State.role === 'resident' ?
            `<button class="icon-btn" onclick="acknowledgeReminder(${r.id})" title="Đánh dấu đã xem">✓</button>` : ''
        }
                </div>
            </td>
        </tr>
    `).join('');
}

function filterReminders() {
    loadReminders();
}

async function generateReminders() {
    try {
        showLoading();
        const result = await apiCall('/reminders/admin/generate', { method: 'POST' });

        if (result) {
            showToast(result.message, 'success');
            loadReminders();
        }
    } catch (error) {
        console.error('Error generating reminders:', error);
        showToast('Không thể tạo nhắc nhở', 'error');
    } finally {
        hideLoading();
    }
}

async function showReminderRulesModal() {
    try {
        showLoading();
        const rules = await apiCall('/reminders/admin/rules');

        if (!rules || rules.length === 0) {
            document.getElementById('reminder-rules-body').innerHTML = `
                <p style="text-align: center; color: #64748b;">Chưa có quy tắc nào</p>
            `;
        } else {
            const ruleTypeLabels = {
                'CCCD_14': '📇 Làm CCCD lần đầu (14 tuổi)',
                'TEMP_RESIDENCE_EXPIRE': '🏠 Tạm trú sắp hết hạn',
                'TEMP_ABSENCE_LONG': '🚶 Tạm vắng quá lâu',
                'LIFE_EVENT': '🎉 Sự kiện cuộc sống'
            };

            document.getElementById('reminder-rules-body').innerHTML = `
                <table class="data-table" style="margin: 0;">
                    <thead>
                        <tr>
                            <th>Quy tắc</th>
                            <th>Nhắc trước (ngày)</th>
                            <th>Trạng thái</th>
                            <th class="text-right">Tác vụ</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rules.map(r => `
                            <tr>
                                <td>
                                    <strong>${ruleTypeLabels[r.rule_type] || r.rule_type}</strong>
                                    <br><small style="color: #64748b;">${r.description || ''}</small>
                                </td>
                                <td>
                                    <input type="number" class="form-control" value="${r.days_before}" 
                                        id="rule-days-${r.id}" style="width: 80px;" min="0" max="365">
                                </td>
                                <td>
                                    <label style="display: flex; align-items: center; gap: 8px;">
                                        <input type="checkbox" id="rule-active-${r.id}" ${r.is_active ? 'checked' : ''}>
                                        ${r.is_active ? 'Bật' : 'Tắt'}
                                    </label>
                                </td>
                                <td class="text-right">
                                    <button class="btn-primary" style="padding: 6px 12px; font-size: 12px;" 
                                        onclick="updateReminderRule(${r.id})">
                                        Lưu
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }

        document.getElementById('reminder-rules-modal').style.display = 'flex';

    } catch (error) {
        console.error('Error loading reminder rules:', error);
        showToast('Không thể tải quy tắc nhắc nhở', 'error');
    } finally {
        hideLoading();
    }
}

async function updateReminderRule(ruleId) {
    const daysBefore = document.getElementById(`rule-days-${ruleId}`).value;
    const isActive = document.getElementById(`rule-active-${ruleId}`).checked;

    try {
        showLoading();
        const result = await apiCall(`/reminders/admin/rules/${ruleId}`, {
            method: 'PUT',
            body: JSON.stringify({
                days_before: parseInt(daysBefore),
                is_active: isActive
            })
        });

        if (result) {
            showToast('Đã cập nhật quy tắc!', 'success');
            showReminderRulesModal(); // Refresh
        }
    } catch (error) {
        console.error('Error updating rule:', error);
        showToast('Không thể cập nhật quy tắc', 'error');
    } finally {
        hideLoading();
    }
}

async function acknowledgeReminder(reminderId) {
    try {
        showLoading();
        const result = await apiCall(`/reminders/${reminderId}/acknowledge`, { method: 'PUT' });

        if (result) {
            showToast('Đã xác nhận!', 'success');
            loadReminders();
        }
    } catch (error) {
        console.error('Error acknowledging reminder:', error);
        showToast('Không thể xác nhận', 'error');
    } finally {
        hideLoading();
    }
}

async function showCreateReminderModal() {
    // Load residents for dropdown
    try {
        showLoading();
        const residents = await apiCall('/persons?limit=500');
        const select = document.getElementById('reminder-resident-id');
        if (select && residents && residents.items) {
            select.innerHTML = '<option value="">-- Chọn cư dân --</option>' +
                residents.items.map(r => `<option value="${r.id}">${r.full_name} - ${r.cccd || 'N/A'}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading residents:', error);
    } finally {
        hideLoading();
    }

    // Clear form
    document.getElementById('reminder-title').value = '';
    document.getElementById('reminder-message').value = '';
    document.getElementById('reminder-due-date').value = '';

    document.getElementById('create-reminder-modal').style.display = 'flex';
}

async function submitCreateReminder() {
    const residentId = document.getElementById('reminder-resident-id').value;
    const title = document.getElementById('reminder-title').value.trim();
    const message = document.getElementById('reminder-message').value.trim();
    const dueDate = document.getElementById('reminder-due-date').value;

    if (!residentId || !title || !message) {
        showToast('Vui lòng điền đầy đủ thông tin', 'error');
        return;
    }

    try {
        showLoading();
        const result = await apiCall('/reminders/admin/create', {
            method: 'POST',
            body: JSON.stringify({
                resident_id: parseInt(residentId),
                title: title,
                message: message,
                due_date: dueDate || null
            })
        });

        if (result) {
            showToast(result.message, 'success');
            closeModal('create-reminder-modal');
            loadReminders();
        }
    } catch (error) {
        console.error('Error creating reminder:', error);
        showToast('Không thể tạo nhắc nhở', 'error');
    } finally {
        hideLoading();
    }
}
