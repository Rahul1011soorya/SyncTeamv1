/**
 * SyncTeam Workspace - Multi-Tenant Authentication Scripts
 * Binds tenant workspace isolation criteria codes onto validation transport packets.
 */

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
    
    const payload = {
        username: document.getElementById('reg_username').value.trim(),
        password: document.getElementById('reg_password').value.trim(),
        real_name: document.getElementById('reg_real_name').value.trim(),
        stream: document.getElementById('reg_stream').value.trim(),
        class_name: document.getElementById('reg_class').value.trim(),
        batch: document.getElementById('reg_batch').value.trim(),
        semester: document.getElementById('reg_semester').value.trim(),
        academic_year: document.getElementById('reg_year').value.trim(),
        role: signupRole,
        inst_code: instCode
    };

    if (signupRole === 'faculty') {
        payload.faculty_id = document.getElementById('reg_faculty_id').value.trim();
        payload.subject = document.getElementById('reg_subject').value.trim();
    } else {
        payload.student_roll_no = document.getElementById('reg_roll_no').value.trim();
    }

    fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        if (data.success) window.location.href = `/portal/${signupRole}?inst_code=${instCode}`;
    });
}