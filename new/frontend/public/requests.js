// ==========================================
// ROLE-BASED ACTION MODALS
// requests.js - Additional functions for role-based UI
// ==========================================

function showAddModal() {
    const currentTab = State.currentTab;
    if (currentTab === 'households') {
        addHousehold();
    } else if (currentTab === 'persons') {
        addPerson();
    } else if (currentTab === 'temporary') {
        showTempAddOptions();
    } else if (currentTab === 'complaints') {
        addComplaint();
    }
}

function showTempAddOptions() {
    showModal('Thêm mới', `
        <div style="display: flex; gap: 16px; justify-content: center;">
            <button class="btn-primary" onclick="closeModal(); addAbsentRequest();" style="padding: 20px 32px;">
                📤 Đăng ký Tạm vắng
            </button>
            <button class="btn-primary" onclick="closeModal(); addTempResidence();" style="padding: 20px 32px;">
                📥 Đăng ký Tạm trú
            </button>
        </div>
    `);
}

function addAbsentRequest() {
    // Load persons first if needed
    if (!State.persons || State.persons.length === 0) {
        loadPersons().then(() => showAbsentForm());
    } else {
        showAbsentForm();
    }
}

function showAbsentForm() {
    const options = State.persons.map(p => `<option value="${p.id}">${p.full_name}</option>`).join('');
    showModal('Đăng ký Tạm vắng', `
        <form id="add-absent-form" onsubmit="handleAddAbsentRequest(event)">
            <div class="form-group">
                <label>Cư dân *</label>
                <select id="absent-resident-id" class="form-control" required>
                    <option value="">-- Chọn cư dân --</option>
                    ${options}
                </select>
            </div>
            <div class="form-group">
                <label>Ngày bắt đầu *</label>
                <input type="date" id="absent-start-date" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Ngày kết thúc *</label>
                <input type="date" id="absent-end-date" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Nơi đến *</label>
                <input type="text" id="absent-destination" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Lý do *</label>
                <textarea id="absent-reason" class="form-control" rows="3" required></textarea>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Gửi yêu cầu</button>
            </div>
        </form>
    `);
}

async function handleAddAbsentRequest(event) {
    event.preventDefault();
    const formData = {
        resident_id: parseInt(document.getElementById('absent-resident-id').value),
        start_date: document.getElementById('absent-start-date').value,
        end_date: document.getElementById('absent-end-date').value,
        destination: document.getElementById('absent-destination').value,
        reason: document.getElementById('absent-reason').value
    };
    try {
        showLoading();
        await apiCall('/absent-requests', { method: 'POST', body: JSON.stringify(formData) });
        showToast('Đã gửi yêu cầu tạm vắng', 'success');
        closeModal();
        loadAbsentRequests();
    } catch (error) {
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}

function addTempResidence() {
    // Load households first if needed
    if (!State.households || State.households.length === 0) {
        loadHouseholds().then(() => showTempResidenceForm());
    } else {
        showTempResidenceForm();
    }
}

function showTempResidenceForm() {
    const options = State.households.map(h => `<option value="${h.id}">${h.household_code} - ${h.address}</option>`).join('');
    showModal('Đăng ký Tạm trú', `
        <form id="add-temp-res-form" onsubmit="handleAddTempResidence(event)">
            <div class="form-group">
                <label>Họ và tên *</label>
                <input type="text" id="temp-full-name" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Ngày sinh *</label>
                <input type="date" id="temp-dob" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Nơi thường trú *</label>
                <input type="text" id="temp-origin" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Hộ gia đình tiếp nhận *</label>
                <select id="temp-household-id" class="form-control" required>
                    <option value="">-- Chọn hộ gia đình --</option>
                    ${options}
                </select>
            </div>
            <div class="form-group">
                <label>Ngày bắt đầu *</label>
                <input type="date" id="temp-start-date" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Ngày kết thúc *</label>
                <input type="date" id="temp-end-date" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Lý do tạm trú *</label>
                <textarea id="temp-reason" class="form-control" rows="3" required></textarea>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-secondary" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn-add">Gửi yêu cầu</button>
            </div>
        </form>
    `);
}

async function handleAddTempResidence(event) {
    event.preventDefault();
    const formData = {
        full_name: document.getElementById('temp-full-name').value,
        dob: document.getElementById('temp-dob').value,
        origin_address: document.getElementById('temp-origin').value,
        host_household_id: parseInt(document.getElementById('temp-household-id').value),
        start_date: document.getElementById('temp-start-date').value,
        end_date: document.getElementById('temp-end-date').value,
        reason: document.getElementById('temp-reason').value
    };
    try {
        showLoading();
        await apiCall('/temp-residences', { method: 'POST', body: JSON.stringify(formData) });
        showToast('Đã gửi yêu cầu tạm trú', 'success');
        closeModal();
        loadTempResidences();
    } catch (error) {
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}


// NOTE: showRequestModal is now defined in app.js with the full dynamic form
// This function was removed to avoid conflicts

// For Leader: View pending requests
async function showPendingRequests() {
    try {
        showLoading();
        const requests = await apiCall('/requests?status_filter=PENDING');
        if (!requests || requests.length === 0) {
            showModal('Yêu cầu chờ duyệt', `
                <div class="text-center" style="padding: 40px;">
                    <div style="font-size: 48px;">✅</div>
                    <p>Không có yêu cầu nào đang chờ duyệt</p>
                </div>
            `);
            return;
        }
        const requestsHtml = requests.map(req => `
            <div style="padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${req.title}</strong>
                        <br><small>Loại: ${req.request_type}</small>
                        <br><small>Người gửi: ${req.requester_name || 'N/A'}</small>
                    </div>
                    <div>
                        <button class="btn-primary" onclick="approveRequest(${req.id})" style="margin-right: 8px;">✓ Duyệt</button>
                        <button class="btn-secondary" onclick="rejectRequest(${req.id})" style="background: #ef4444; color: white;">✗ Từ chối</button>
                    </div>
                </div>
            </div>
        `).join('');
        showModal('Yêu cầu chờ duyệt (' + requests.length + ')', requestsHtml);
    } catch (error) {
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}

async function approveRequest(requestId) {
    try {
        showLoading();
        await apiCall('/requests/' + requestId, {
            method: 'PUT',
            body: JSON.stringify({ status: 'APPROVED', approval_note: 'Đã duyệt' })
        });
        showToast('Đã duyệt yêu cầu', 'success');
        closeModal();
        showPendingRequests();
    } catch (error) {
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}

async function rejectRequest(requestId) {
    const note = prompt('Lý do từ chối:');
    if (note === null) return;
    try {
        showLoading();
        await apiCall('/requests/' + requestId, {
            method: 'PUT',
            body: JSON.stringify({ status: 'REJECTED', approval_note: note || 'Từ chối' })
        });
        showToast('Đã từ chối yêu cầu', 'success');
        closeModal();
        showPendingRequests();
    } catch (error) {
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}
