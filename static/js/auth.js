/**
 * SyncTeam Workspace - Multi-Tenant Authentication Scripts
 * Binds tenant workspace isolation criteria codes onto validation transport packets.
 */

function notifySync(message, type = "success", afterClose = null) {
    if (window.showSyncToast) showSyncToast(message, type, afterClose);
    else alert(message);
}

function executeAuthentication() {
    const userIn = document.getElementById('username').value.trim();
    const passIn = document.getElementById('password').value.trim();
    const instCode = document.getElementById('active_inst_context').value;
    const errorBox = document.getElementById('auth-error');
    
    const segmentedPath = window.location.pathname.split('/');
    const roleContext = segmentedPath[segmentedPath.length - 1];

    errorBox.style.display = 'none';

    fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            username: userIn, password: passIn, role: roleContext, inst_code: instCode 
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            if (roleContext === 'admin') window.location.href = '/admin/dashboard';
            else if (roleContext === 'faculty') window.location.href = '/faculty/dashboard';
            else window.location.href = '/student/dashboard';
        } else {
            errorBox.innerText = data.message;
            errorBox.style.display = 'block';
        }
    });
}

function executeRegistration() {
    const segmentedPath = window.location.pathname.split('/');
    const signupRole = segmentedPath[segmentedPath.length - 1];
    const instCode = document.getElementById('active_inst_context').value;
    
    const valueFor = (id) => {
        const field = document.getElementById(id);
        return field ? field.value.trim() : "";
    };

    const payload = {
        username: valueFor('reg_username'),
        password: valueFor('reg_password'),
        real_name: valueFor('reg_real_name').toUpperCase(),
        stream: valueFor('reg_stream'),
        class_name: valueFor('reg_class'),
        batch: valueFor('reg_batch'),
        semester: valueFor('reg_semester'),
        academic_year: valueFor('reg_year'),
        role: signupRole,
        inst_code: instCode
    };

    if (signupRole === 'faculty') {
        payload.faculty_id = valueFor('reg_faculty_id').toUpperCase();
        payload.subject = valueFor('reg_subject');
    } else {
        payload.student_roll_no = valueFor('reg_roll_no').toUpperCase();
    }

    fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        notifySync(data.message, data.success ? "success" : "error", data.success ? () => {
            window.location.href = `/portal/${signupRole}?inst_code=${instCode}`;
        } : null);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.caps-only').forEach(field => {
        field.addEventListener('input', () => {
            field.value = field.value.toUpperCase();
        });
    });
});
