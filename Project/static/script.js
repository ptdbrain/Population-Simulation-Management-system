// Global variables
let currentSection = 'households';
let editingId = null;
let authToken = null;
let currentUser = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initAuth();
    refreshDataByRole();
    
    // Set today's date as default for date inputs
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(input => {
        if (!input.value) {
            input.value = today;
        }
    });
    bindAuthForms();
});

function initAuth() {
    authToken = localStorage.getItem('token');
    if (authToken) {
        fetch('/api/me', { headers: { 'Authorization': `Bearer ${authToken}` } })
            .then(r => r.ok ? r.json() : null)
            .then(user => {
                if (user) {
                    currentUser = user;
                    updateAuthUI(true);
                } else {
                    updateAuthUI(false);
                }
            })
            .catch(() => updateAuthUI(false));
    } else {
        updateAuthUI(false);
    }
}

function updateAuthUI(isLoggedIn) {
    const info = document.getElementById('authUserInfo');
    const actions = document.getElementById('authActions');
    if (!info || !actions) return;
    if (isLoggedIn && currentUser) {
        info.style.display = '';
        actions.style.display = 'none';
        document.getElementById('authUsername').textContent = currentUser.username;
        document.getElementById('authRole').textContent = currentUser.role;
    } else {
        info.style.display = 'none';
        actions.style.display = '';
    }
}

function bindAuthForms() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', login);
    }
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', register);
    }
}

async function login(e) {
    e.preventDefault();
    const form = e.target;
    const username = form.username.value.trim();
    const password = form.password.value;
    try {
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('password', password);
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params
        });
        if (!res.ok) throw new Error('Login failed');
        const data = await res.json();
        authToken = data.access_token;
        localStorage.setItem('token', authToken);
        const meRes = await fetch('/api/me', { headers: { 'Authorization': `Bearer ${authToken}` } });
        currentUser = await meRes.json();
        updateAuthUI(true);
        closeModal('loginModal');
        showMessage('Đăng nhập thành công', 'success');
        refreshDataByRole();
    } catch (err) {
        showMessage('Đăng nhập thất bại', 'error');
    }
}

async function register(e) {
    e.preventDefault();
    const form = e.target;
    const payload = {
        username: form.username.value.trim(),
        password: form.password.value,
        full_name: form.full_name.value.trim() || null
    };
    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Register failed');
        showMessage('Đăng ký thành công, vui lòng đăng nhập', 'success');
        closeModal('registerModal');
        openModal('loginModal');
    } catch (err) {
        showMessage('Đăng ký thất bại', 'error');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('token');
    updateAuthUI(false);
    showMessage('Đã đăng xuất', 'success');
}

function authHeaders(extra = {}) {
    return authToken ? { 'Authorization': `Bearer ${authToken}`, ...extra } : { ...extra };
}

function refreshDataByRole() {
    // For all users, attempt to load self-service and admin views; protected calls will error if not authorized
    loadHouseholds();
    loadPersons();
    loadAbsences();
    loadResidences();
    loadFeedbacks();
    loadStatistics();
}

// Navigation functions
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Remove active class from all nav links
    document.querySelectorAll('nav a').forEach(link => {
        link.classList.remove('active');
    });
    
    // Show selected section
    document.getElementById(sectionId).classList.add('active');
    
    // Add active class to clicked nav link
    event.target.classList.add('active');
    
    currentSection = sectionId;
}

function showTab(tabId) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabId).classList.add('active');
    
    // Add active class to clicked tab button
    event.target.classList.add('active');
}

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    editingId = null;
    
    // Clear form if it's a new entry
    const form = document.querySelector(`#${modalId} form`);
    if (form) {
        form.reset();
    }
    
    // Load persons for dropdowns if needed
    if (modalId === 'absenceModal' || modalId === 'residenceModal') {
        loadPersonsForDropdown();
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    editingId = null;
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
        editingId = null;
    }
}

// API functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders(options.headers || {})
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showMessage('Có lỗi xảy ra khi kết nối với server', 'error');
        throw error;
    }
}

// Household functions
async function loadHouseholds() {
    try {
        const households = await apiCall('/api/households/');
        displayHouseholds(households);
    } catch (error) {
        console.error('Failed to load households:', error);
    }
}

function displayHouseholds(households) {
    const tbody = document.getElementById('householdsTableBody');
    tbody.innerHTML = '';
    
    if (households.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state"><i class="fas fa-home"></i><h3>Chưa có hộ khẩu nào</h3><p>Hãy thêm hộ khẩu đầu tiên</p></td></tr>';
        return;
    }
    
    households.forEach(household => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${household.household_number}</td>
            <td>${household.address}</td>
            <td>${household.members ? household.members.length : 0}</td>
            <td>${formatDate(household.created_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-primary" onclick="editHousehold('${household.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger" onclick="deleteHousehold('${household.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function saveHousehold(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const household = {
        household_number: formData.get('household_number'),
        address: formData.get('address')
    };
    
    try {
        if (editingId) {
            await apiCall(`/api/households/${editingId}`, {
                method: 'PUT',
                body: JSON.stringify(household)
            });
            showMessage('Cập nhật hộ khẩu thành công', 'success');
        } else {
            await apiCall('/api/households/', {
                method: 'POST',
                body: JSON.stringify(household)
            });
            showMessage('Thêm hộ khẩu thành công', 'success');
        }
        
        closeModal('householdModal');
        loadHouseholds();
    } catch (error) {
        console.error('Failed to save household:', error);
    }
}

async function editHousehold(id) {
    try {
        const household = await apiCall(`/api/households/${id}`);
        
        document.getElementById('householdNumber').value = household.household_number;
        document.getElementById('householdAddress').value = household.address;
        
        editingId = id;
        openModal('householdModal');
    } catch (error) {
        console.error('Failed to load household:', error);
    }
}

async function deleteHousehold(id) {
    if (confirm('Bạn có chắc chắn muốn xóa hộ khẩu này?')) {
        try {
            await apiCall(`/api/households/${id}`, {
                method: 'DELETE'
            });
            showMessage('Xóa hộ khẩu thành công', 'success');
            loadHouseholds();
        } catch (error) {
            console.error('Failed to delete household:', error);
        }
    }
}

// Person functions
async function loadPersons() {
    try {
        const persons = await apiCall('/api/persons/');
        displayPersons(persons);
    } catch (error) {
        console.error('Failed to load persons:', error);
    }
}

function displayPersons(persons) {
    const tbody = document.getElementById('personsTableBody');
    tbody.innerHTML = '';
    
    if (persons.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><i class="fas fa-user"></i><h3>Chưa có nhân khẩu nào</h3><p>Hãy thêm nhân khẩu đầu tiên</p></td></tr>';
        return;
    }
    
    persons.forEach(person => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${person.name}</td>
            <td>${formatDate(person.birth_date)}</td>
            <td>${person.gender === 'nam' ? 'Nam' : 'Nữ'}</td>
            <td>${person.id_number}</td>
            <td>${getRelationshipText(person.relationship)}</td>
            <td>${person.occupation}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-primary" onclick="editPerson('${person.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger" onclick="deletePerson('${person.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function savePerson(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const person = {
        name: formData.get('name'),
        birth_date: formData.get('birth_date'),
        gender: formData.get('gender'),
        id_number: formData.get('id_number'),
        relationship: formData.get('relationship'),
        occupation: formData.get('occupation'),
        address: formData.get('address'),
        phone: formData.get('phone')
    };
    
    try {
        if (editingId) {
            await apiCall(`/api/persons/${editingId}`, {
                method: 'PUT',
                body: JSON.stringify(person)
            });
            showMessage('Cập nhật nhân khẩu thành công', 'success');
        } else {
            await apiCall('/api/persons/', {
                method: 'POST',
                body: JSON.stringify(person)
            });
            showMessage('Thêm nhân khẩu thành công', 'success');
        }
        
        closeModal('personModal');
        loadPersons();
    } catch (error) {
        console.error('Failed to save person:', error);
    }
}

async function editPerson(id) {
    try {
        const person = await apiCall(`/api/persons/${id}`);
        
        document.getElementById('personName').value = person.name;
        document.getElementById('personBirthDate').value = person.birth_date;
        document.getElementById('personGender').value = person.gender;
        document.getElementById('personIdNumber').value = person.id_number;
        document.getElementById('personRelationship').value = person.relationship;
        document.getElementById('personOccupation').value = person.occupation;
        document.getElementById('personAddress').value = person.address;
        document.getElementById('personPhone').value = person.phone || '';
        
        editingId = id;
        openModal('personModal');
    } catch (error) {
        console.error('Failed to load person:', error);
    }
}

async function deletePerson(id) {
    if (confirm('Bạn có chắc chắn muốn xóa nhân khẩu này?')) {
        try {
            await apiCall(`/api/persons/${id}`, {
                method: 'DELETE'
            });
            showMessage('Xóa nhân khẩu thành công', 'success');
            loadPersons();
        } catch (error) {
            console.error('Failed to delete person:', error);
        }
    }
}

// Temporary absence functions
async function loadAbsences() {
    try {
        const absences = await apiCall('/api/temporary-absences/');
        displayAbsences(absences);
    } catch (error) {
        console.error('Failed to load absences:', error);
    }
}

function displayAbsences(absences) {
    const tbody = document.getElementById('absencesTableBody');
    tbody.innerHTML = '';
    
    if (absences.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><i class="fas fa-user-minus"></i><h3>Chưa có tạm vắng nào</h3><p>Hãy thêm tạm vắng đầu tiên</p></td></tr>';
        return;
    }
    
    absences.forEach(absence => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${absence.person_name}</td>
            <td>${absence.household_number}</td>
            <td>${formatDate(absence.start_date)}</td>
            <td>${formatDate(absence.end_date)}</td>
            <td>${absence.reason}</td>
            <td><span class="status-badge status-${absence.status}">${absence.status}</span></td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-danger" onclick="deleteAbsence('${absence.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function saveAbsence(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const absence = {
        person_id: formData.get('person_id'),
        start_date: formData.get('start_date'),
        end_date: formData.get('end_date'),
        reason: formData.get('reason')
    };
    
    try {
        await apiCall('/api/temporary-absences/', {
            method: 'POST',
            body: JSON.stringify(absence)
        });
        
        showMessage('Thêm tạm vắng thành công', 'success');
        closeModal('absenceModal');
        loadAbsences();
    } catch (error) {
        console.error('Failed to save absence:', error);
    }
}

async function deleteAbsence(id) {
    if (confirm('Bạn có chắc chắn muốn xóa tạm vắng này?')) {
        try {
            await apiCall(`/api/temporary-absences/${id}`, {
                method: 'DELETE'
            });
            showMessage('Xóa tạm vắng thành công', 'success');
            loadAbsences();
        } catch (error) {
            console.error('Failed to delete absence:', error);
        }
    }
}

// Temporary residence functions
async function loadResidences() {
    try {
        const residences = await apiCall('/api/temporary-residences/');
        displayResidences(residences);
    } catch (error) {
        console.error('Failed to load residences:', error);
    }
}

function displayResidences(residences) {
    const tbody = document.getElementById('residencesTableBody');
    tbody.innerHTML = '';
    
    if (residences.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><i class="fas fa-user-plus"></i><h3>Chưa có tạm trú nào</h3><p>Hãy thêm tạm trú đầu tiên</p></td></tr>';
        return;
    }
    
    residences.forEach(residence => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${residence.person_name}</td>
            <td>${residence.household_number}</td>
            <td>${formatDate(residence.start_date)}</td>
            <td>${formatDate(residence.end_date)}</td>
            <td>${residence.reason}</td>
            <td><span class="status-badge status-${residence.status}">${residence.status}</span></td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-danger" onclick="deleteResidence('${residence.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function saveResidence(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const residence = {
        person_id: formData.get('person_id'),
        start_date: formData.get('start_date'),
        end_date: formData.get('end_date'),
        reason: formData.get('reason')
    };
    
    try {
        await apiCall('/api/temporary-residences/', {
            method: 'POST',
            body: JSON.stringify(residence)
        });
        
        showMessage('Thêm tạm trú thành công', 'success');
        closeModal('residenceModal');
        loadResidences();
    } catch (error) {
        console.error('Failed to save residence:', error);
    }
}

async function deleteResidence(id) {
    if (confirm('Bạn có chắc chắn muốn xóa tạm trú này?')) {
        try {
            await apiCall(`/api/temporary-residences/${id}`, {
                method: 'DELETE'
            });
            showMessage('Xóa tạm trú thành công', 'success');
            loadResidences();
        } catch (error) {
            console.error('Failed to delete residence:', error);
        }
    }
}

// Feedback functions
async function loadFeedbacks() {
    try {
        const feedbacks = await apiCall('/api/feedbacks/');
        displayFeedbacks(feedbacks);
    } catch (error) {
        console.error('Failed to load feedbacks:', error);
    }
}

function displayFeedbacks(feedbacks) {
    const tbody = document.getElementById('feedbacksTableBody');
    tbody.innerHTML = '';
    
    if (feedbacks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><i class="fas fa-comments"></i><h3>Chưa có phản ánh/Kiến nghị nào</h3><p>Hãy thêm phản ánh/Kiến nghị đầu tiên</p></td></tr>';
        return;
    }
    
    feedbacks.forEach(feedback => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${feedback.person_name}</td>
            <td>${feedback.content}</td>
            <td>${formatDate(feedback.date)}</td>
            <td>${getCategoryText(feedback.category)}</td>
            <td><span class="status-badge status-${feedback.status}">${getStatusText(feedback.status)}</span></td>
            <td>${feedback.response || 'Chưa có'}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-primary" onclick="editFeedback('${feedback.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger" onclick="deleteFeedback('${feedback.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function saveFeedback(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const feedback = {
        person_name: formData.get('person_name'),
        content: formData.get('content'),
        date: formData.get('date'),
        category: formData.get('category'),
        response: formData.get('response')
    };
    
    try {
        if (editingId) {
            await apiCall(`/api/feedbacks/${editingId}`, {
                method: 'PUT',
                body: JSON.stringify(feedback)
            });
            showMessage('Cập nhật phản ánh/Kiến nghị thành công', 'success');
        } else {
            await apiCall('/api/feedbacks/', {
                method: 'POST',
                body: JSON.stringify(feedback)
            });
            showMessage('Thêm phản ánh/Kiến nghị thành công', 'success');
        }
        
        closeModal('feedbackModal');
        loadFeedbacks();
    } catch (error) {
        console.error('Failed to save feedback:', error);
    }
}

async function editFeedback(id) {
    try {
        const feedback = await apiCall(`/api/feedbacks/${id}`);
        
        document.getElementById('feedbackPerson').value = feedback.person_name;
        document.getElementById('feedbackContent').value = feedback.content;
        document.getElementById('feedbackDate').value = feedback.date;
        document.getElementById('feedbackCategory').value = feedback.category;
        document.getElementById('feedbackResponse').value = feedback.response || '';
        
        editingId = id;
        openModal('feedbackModal');
    } catch (error) {
        console.error('Failed to load feedback:', error);
    }
}

async function deleteFeedback(id) {
    if (confirm('Bạn có chắc chắn muốn xóa phản ánh/Kiến nghị này?')) {
        try {
            await apiCall(`/api/feedbacks/${id}`, {
                method: 'DELETE'
            });
            showMessage('Xóa phản ánh/Kiến nghị thành công', 'success');
            loadFeedbacks();
        } catch (error) {
            console.error('Failed to delete feedback:', error);
        }
    }
}

// Statistics functions
async function loadStatistics() {
    try {
        const [genderStats, ageStats, feedbackStats] = await Promise.all([
            apiCall('/api/statistics/population-by-gender'),
            apiCall('/api/statistics/population-by-age'),
            apiCall('/api/statistics/feedbacks-by-status')
        ]);
        
        displayGenderStats(genderStats);
        displayAgeStats(ageStats);
        displayFeedbackStats(feedbackStats);
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

function displayGenderStats(stats) {
    const container = document.getElementById('genderStats');
    container.innerHTML = '';
    
    if (stats.length === 0) {
        container.innerHTML = '<p>Chưa có dữ liệu</p>';
        return;
    }
    
    stats.forEach(stat => {
        const div = document.createElement('div');
        div.className = 'stat-item';
        div.innerHTML = `
            <span>${stat.gender === 'nam' ? 'Nam' : 'Nữ'}</span>
            <span>${stat.count}</span>
        `;
        container.appendChild(div);
    });
}

function displayAgeStats(stats) {
    const container = document.getElementById('ageStats');
    container.innerHTML = '';
    
    if (stats.length === 0) {
        container.innerHTML = '<p>Chưa có dữ liệu</p>';
        return;
    }
    
    stats.forEach(stat => {
        const div = document.createElement('div');
        div.className = 'stat-item';
        div.innerHTML = `
            <span>${stat.age_group}</span>
            <span>${stat.count}</span>
        `;
        container.appendChild(div);
    });
}

function displayFeedbackStats(stats) {
    const container = document.getElementById('feedbackStats');
    container.innerHTML = '';
    
    if (stats.length === 0) {
        container.innerHTML = '<p>Chưa có dữ liệu</p>';
        return;
    }
    
    stats.forEach(stat => {
        const div = document.createElement('div');
        div.className = 'stat-item';
        div.innerHTML = `
            <span>${getStatusText(stat.status)}</span>
            <span>${stat.count}</span>
        `;
        container.appendChild(div);
    });
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN');
}

function getRelationshipText(relationship) {
    const relationships = {
        'chu_ho': 'Chủ hộ',
        'vo': 'Vợ',
        'chong': 'Chồng',
        'con': 'Con',
        'cha': 'Cha',
        'me': 'Mẹ',
        'anh_em': 'Anh/Em',
        'khac': 'Khác'
    };
    return relationships[relationship] || relationship;
}

function getCategoryText(category) {
    const categories = {
        'phan_anh': 'Phản ánh',
        'kien_nghi': 'Kiến nghị',
        'khac': 'Khác'
    };
    return categories[category] || category;
}

function getStatusText(status) {
    const statuses = {
        'new': 'Mới',
        'processing': 'Đang xử lý',
        'resolved': 'Đã giải quyết',
        'active': 'Hoạt động',
        'expired': 'Hết hạn'
    };
    return statuses[status] || status;
}

function showMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    
    const main = document.querySelector('main');
    main.insertBefore(messageDiv, main.firstChild);
    
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

async function loadPersonsForDropdown() {
    try {
        const persons = await apiCall('/api/persons/');
        const absenceSelect = document.getElementById('absencePerson');
        const residenceSelect = document.getElementById('residencePerson');
        
        // Clear existing options
        absenceSelect.innerHTML = '<option value="">Chọn nhân khẩu</option>';
        residenceSelect.innerHTML = '<option value="">Chọn nhân khẩu</option>';
        
        persons.forEach(person => {
            const option1 = document.createElement('option');
            option1.value = person.id;
            option1.textContent = person.name;
            absenceSelect.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = person.id;
            option2.textContent = person.name;
            residenceSelect.appendChild(option2);
        });
    } catch (error) {
        console.error('Failed to load persons for dropdown:', error);
    }
}

// Search functions
function searchHouseholds() {
    const searchTerm = document.getElementById('householdSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#householdsTableBody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

function searchPersons() {
    const searchTerm = document.getElementById('personSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#personsTableBody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

// Form event listeners
document.getElementById('householdForm').addEventListener('submit', saveHousehold);
document.getElementById('personForm').addEventListener('submit', savePerson);
document.getElementById('absenceForm').addEventListener('submit', saveAbsence);
document.getElementById('residenceForm').addEventListener('submit', saveResidence);
document.getElementById('feedbackForm').addEventListener('submit', saveFeedback);
