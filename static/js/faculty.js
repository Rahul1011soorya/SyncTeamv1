const selectedCohorts = [];

function notifySync(message, type = "success", afterClose = null) {
    if (window.showSyncToast) showSyncToast(message, type, afterClose);
    else alert(message);
}

function fieldValue(id) {
    const field = document.getElementById(id);
    return field ? field.value.trim() : "";
}

function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#039;"
    }[char]));
}

function discoverStudentsByAttributes() {
    const queryParams = new URLSearchParams({
        stream: fieldValue('filter_stream'),
        class_name: fieldValue('filter_class'),
        batch: fieldValue('filter_batch'),
        semester: fieldValue('filter_semester'),
        academic_year: fieldValue('filter_year'),
        department: fieldValue('filter_department'),
        section: fieldValue('filter_section')
    });

    fetch(`/api/reports/discover-students?${queryParams.toString()}`)
    .then(res => res.json())
    .then(students => {
        const tableBody = document.getElementById('discovered-students-rows');
        if (!tableBody) return;
        tableBody.innerHTML = "";

        if (students.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7">No records matched these filters.</td></tr>`;
            return;
        }

        students.forEach(s => {
            tableBody.innerHTML += `
                <tr>
                    <td><strong>${escapeHtml(s.name)}</strong></td>
                    <td><code>${escapeHtml(s.roll_no)}</code></td>
                    <td>${escapeHtml(s.age || '-')}</td>
                    <td>${escapeHtml(s.enrollment_year || '-')}</td>
                    <td>${escapeHtml(s.stream)}</td>
                    <td>${escapeHtml(s.class)} [${escapeHtml(s.batch)}]</td>
                    <td>${escapeHtml(s.year)}</td>
                </tr>
            `;
        });
    });
}

function approveFacultyAccess(userId) {
    fetch(`/api/admin/approve-faculty/${userId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        notifySync(data.message || data.error || "Faculty approval request completed.", data.success ? "success" : "error");
        if (!data.success) return;

        const row = document.getElementById(`pending-faculty-${userId}`);
        if (row) row.remove();

        const pendingRows = document.getElementById('pending-faculty-rows');
        if (pendingRows && pendingRows.children.length === 0) {
            pendingRows.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--slate-600);">No faculty accounts are waiting for approval.</td></tr>`;
        }

        if (document.getElementById('teacher-directory-rows')) {
            filterTeacherDirectory();
        }
    })
    .catch(() => notifySync("Unable to approve faculty access. Please try again.", "error"));
}

function createAdminManagedUser() {
    const role = fieldValue('admin_new_role');
    const payload = {
        role,
        real_name: fieldValue('admin_new_name'),
        username: fieldValue('admin_new_username'),
        password: fieldValue('admin_new_password'),
        stream: fieldValue('admin_new_stream'),
        class_name: fieldValue('admin_new_class'),
        batch: fieldValue('admin_new_batch'),
        semester: fieldValue('admin_new_semester'),
        academic_year: fieldValue('admin_new_year'),
        age: fieldValue('admin_new_age'),
        enrollment_year: fieldValue('admin_new_enrollment_year'),
        student_roll_no: fieldValue('admin_new_roll_no'),
        faculty_id: fieldValue('admin_new_faculty_id'),
        subject_specialization: fieldValue('admin_new_subject')
    };

    fetch('/api/admin/create-user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        notifySync(data.message || data.error || "User creation completed.", data.success ? "success" : "error");
        if (data.success) {
            document.querySelectorAll('.admin-new-user-field').forEach(field => field.value = "");
            if (document.getElementById('teacher-directory-rows')) filterTeacherDirectory();
        }
    })
    .catch(() => notifySync("Unable to create user. Please try again.", "error"));
}

function filterTeacherDirectory() {
    const queryParams = new URLSearchParams({
        department: fieldValue('teacher_filter_department')
    });

    fetch(`/api/admin/teacher-directory?${queryParams.toString()}`)
    .then(res => res.json())
    .then(faculty => {
        const tableBody = document.getElementById('teacher-directory-rows');
        if (!tableBody) return;
        tableBody.innerHTML = "";

        if (faculty.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--slate-600);">No teachers matched this filter.</td></tr>`;
            return;
        }

        faculty.forEach(f => {
            tableBody.innerHTML += `
                <tr>
                    <td><strong>${escapeHtml(f.name)}</strong></td>
                    <td><code>${escapeHtml(f.faculty_id || '-')}</code></td>
                    <td>${escapeHtml(f.department || '-')}</td>
                    <td>${escapeHtml(f.subject || '-')}</td>
                    <td>${escapeHtml(f.status)}</td>
                </tr>
            `;
        });
    });
}

function drawCompletionBarChart(canvasId, legendId, rows, emptyMessage) {
    const canvas = document.getElementById(canvasId);
    const legend = document.getElementById(legendId);
    if (!canvas || !legend) return;

    if (!Array.isArray(rows) || rows.length === 0) {
        const context = canvas.getContext('2d');
        context.clearRect(0, 0, canvas.width, canvas.height);
        legend.innerHTML = `<p class="muted-text">${escapeHtml(emptyMessage)}</p>`;
        return;
    }

    const ratio = window.devicePixelRatio || 1;
    const displayWidth = Math.max(320, canvas.parentElement.clientWidth);
    const displayHeight = Number(canvas.getAttribute('height')) || 240;
    canvas.width = displayWidth * ratio;
    canvas.height = displayHeight * ratio;
    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;

    const ctx = canvas.getContext('2d');
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, displayWidth, displayHeight);

    const palette = ['#2563eb', '#059669', '#dc2626', '#d97706', '#7c3aed', '#0891b2', '#be123c', '#4f46e5'];
    const padding = { top: 22, right: 24, bottom: 54, left: 46 };
    const chartWidth = displayWidth - padding.left - padding.right;
    const chartHeight = displayHeight - padding.top - padding.bottom;
    const barGap = 12;
    const barWidth = Math.max(20, (chartWidth - (rows.length - 1) * barGap) / rows.length);

    ctx.strokeStyle = '#dbe4ef';
    ctx.lineWidth = 1;
    ctx.font = '12px Arial';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    [0, 25, 50, 75, 100].forEach(tick => {
        const y = padding.top + chartHeight - (tick / 100) * chartHeight;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(displayWidth - padding.right, y);
        ctx.stroke();
        ctx.fillText(`${tick}%`, padding.left - 8, y);
    });

    rows.forEach((row, index) => {
        const completion = Math.max(0, Math.min(100, Number(row.completion) || 0));
        const barHeight = (completion / 100) * chartHeight;
        const x = padding.left + index * (barWidth + barGap);
        const y = padding.top + chartHeight - barHeight;
        const color = palette[index % palette.length];

        ctx.fillStyle = color;
        ctx.fillRect(x, y, barWidth, barHeight);

        ctx.fillStyle = '#0f172a';
        ctx.font = '700 12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillText(`${completion}%`, x + barWidth / 2, Math.max(y - 6, 16));

        ctx.save();
        ctx.translate(x + barWidth / 2, padding.top + chartHeight + 8);
        ctx.rotate(-0.45);
        ctx.fillStyle = '#475569';
        ctx.font = '11px Arial';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(row.label).slice(0, 18), 0, 0);
        ctx.restore();
    });

    legend.innerHTML = rows.map((row, index) => `
        <span class="chart-legend-item">
            <i style="background:${palette[index % palette.length]}"></i>
            ${escapeHtml(row.label)} - ${Math.max(0, Math.min(100, Number(row.completion) || 0))}%
            ${row.meta ? `<small>${escapeHtml(row.meta)}</small>` : ""}
        </span>
    `).join("");
}

function loadFacultyProjectCompletionGraph() {
    const chart = document.getElementById('faculty-project-completion-chart');
    if (!chart) return;

    fetch('/api/faculty/project-completion-summary')
    .then(res => res.json())
    .then(projects => {
        drawCompletionBarChart(
            'faculty-project-completion-canvas',
            'faculty-project-completion-legend',
            Array.isArray(projects) ? projects.map(project => ({
                label: project.name,
                completion: project.completion,
                meta: `${project.assigned_students} assigned students | ${project.teams} teams`
            })) : [],
            'No projects available for completion tracking.'
        );
    })
    .catch(() => {
        chart.innerHTML = `<p class="muted-text">Unable to load project completion graph.</p>`;
    });
}

function loadTeamCompletionGraph(projectId) {
    const chart = document.getElementById(`team-completion-chart-${projectId}`);
    if (!chart) return;

    fetch(`/api/faculty/project/${projectId}/team-completion`)
    .then(res => res.json())
    .then(teams => {
        drawCompletionBarChart(
            `team-completion-canvas-${projectId}`,
            `team-completion-legend-${projectId}`,
            Array.isArray(teams) ? teams.map(team => ({
                label: `Team ${team.team_number}`,
                completion: team.completion,
                meta: `${team.members} members | ${team.summary}`
            })) : [],
            'Generate teams to see team-wise completion.'
        );
    })
    .catch(() => {
        chart.innerHTML = `<p class="muted-text">Unable to load team completion graph.</p>`;
    });
}

function renderSelectedCohorts() {
    const container = document.getElementById('selected-cohorts');
    if (!container) return;
    container.innerHTML = selectedCohorts.map((cohort, index) => `
        <button type="button" class="chip-btn" onclick="removeCohortTarget(${index})">
            ${escapeHtml(cohort.academic_year)} / ${escapeHtml(cohort.department)} / ${escapeHtml(cohort.class_name)} x
        </button>
    `).join("");
}

function addCohortTarget() {
    const cohort = {
        academic_year: fieldValue('cohort_year'),
        department: fieldValue('cohort_department'),
        class_name: fieldValue('cohort_class')
    };
    if (!cohort.academic_year || !cohort.department || !cohort.class_name) return;
    const exists = selectedCohorts.some(c => c.academic_year === cohort.academic_year && c.department === cohort.department && c.class_name === cohort.class_name);
    if (!exists) selectedCohorts.push(cohort);
    renderSelectedCohorts();
}

function removeCohortTarget(index) {
    selectedCohorts.splice(index, 1);
    renderSelectedCohorts();
}

function addFlashcardRow() {
    const container = document.getElementById('flashcard-builder');
    if (!container) return;
    const index = container.children.length + 1;
    container.insertAdjacentHTML('beforeend', `
        <div class="flashcard-row">
            <div class="input-set"><label>Topic tag</label><input type="text" class="flash-topic" placeholder="Topic ${index}"></div>
            <div class="input-set"><label>Question</label><textarea class="flash-question" rows="2"></textarea></div>
            <div class="input-set"><label>Answer guide</label><textarea class="flash-guide" rows="2"></textarea></div>
            <div class="input-set"><label>Max marks</label><input type="number" class="flash-marks" min="1" value="10"></div>
            <button type="button" class="btn danger-btn" onclick="this.closest('.flashcard-row').remove()">Remove</button>
        </div>
    `);
}

function injectCustomSkillToForm() {
    const input = document.getElementById('custom_skill_entry');
    const skillName = input ? input.value.trim() : "";
    if (!skillName) return;
    const container = document.querySelector('.checkbox-matrix');
    container.insertAdjacentHTML('beforeend', `<label class="matrix-cb-label"><input type="checkbox" class="skill-checkbox" value="${escapeHtml(skillName)}" checked> ${escapeHtml(skillName)}</label>`);
    input.value = "";
}

function compileAndPublishProject() {
    const selectedSkills = [...document.querySelectorAll('.skill-checkbox:checked')].map(cb => cb.value);
    const flashcards = [...document.querySelectorAll('.flashcard-row')].map(row => ({
        topic_tag: row.querySelector('.flash-topic').value.trim() || "General",
        question: row.querySelector('.flash-question').value.trim(),
        answer_guide: row.querySelector('.flash-guide').value.trim(),
        max_marks: row.querySelector('.flash-marks').value || 10
    })).filter(card => card.question && card.answer_guide);

    if (!fieldValue('p_name') || !fieldValue('p_desc') || !fieldValue('p_deadline') || selectedCohorts.length === 0) {
        notifySync("Fill the project title, brief, deadline, and at least one cohort.", "error");
        return;
    }

    fetch('/api/project/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: fieldValue('p_name'),
            description: fieldValue('p_desc'),
            batch: "Multi-cohort",
            team_size: fieldValue('p_team_size'),
            deadline: fieldValue('p_deadline'),
            cohorts: selectedCohorts,
            skills: selectedSkills,
            flashcards
        })
    })
    .then(res => res.json())
    .then(data => {
        notifySync(data.message, data.success ? "success" : "error", data.success ? () => {
            window.location.href = '/faculty/dashboard';
        } : null);
    });
}

function fetchComplianceTimelineLog(projectId) {
    const listArea = document.getElementById(`compliance-outstanding-log-${projectId}`);
    if (!listArea) return;
    fetch(`/api/faculty/compliance-report/${projectId}`)
    .then(res => res.json())
    .then(students => {
        if (students.length === 0) {
            listArea.innerHTML = `<span class="good-text">All assigned students have submitted skill assessments.</span>`;
            return;
        }
        listArea.innerHTML = `<strong>${students.length} assessment pending</strong>` + students.map(s => `<span>${escapeHtml(s.name)} <code>${escapeHtml(s.roll_no)}</code></span>`).join("");
    });
}

function runTeamMatchmakingOptimization(projectId) {
    fetch(`/api/project/${projectId}/generate-teams`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        notifySync(data.message, data.success ? "success" : "error");
        if (data.success) {
            loadRosterPrintData(projectId);
            loadTeamCompletionGraph(projectId);
            loadFacultyProjectCompletionGraph();
        }
    });
}

function loadRosterPrintData(projectId) {
    Promise.all([
        fetch(`/api/project/${projectId}/roster-report`).then(res => res.json()),
        fetch(`/api/project/${projectId}/eligible-students`).then(res => res.json())
    ]).then(([reportData, eligible]) => {
        // Safely unpack the updated backend nested structure
        const teams = reportData.teams || {};
        const overlaps = reportData.overlaps || {};
        
        const output = document.getElementById(`teams-allocation-view-${projectId}`);
        const eligibleStrip = document.getElementById(`eligible-students-${projectId}`);
        if (!output) return;
        output.innerHTML = "";

        if (Object.keys(teams).length === 0) {
            output.innerHTML = `<p class="muted-text">No team allocation exists yet.</p>`;
        }

        const teamNumbers = Object.keys(teams);
        const teamOptions = teamNumbers.map(num => `<option value="${num}">Team ${num}</option>`).join("");

        Object.entries(teams).forEach(([teamNum, members]) => {
            const options = Object.keys(teams).map(num => `<option value="${num}">Team ${num}</option>`).join("");
            const teamOverlap = overlaps[teamNum] || "No schedule details recorded";
            
            output.innerHTML += `
                <div class="team-card" style="page-break-inside: avoid; margin-bottom: 1.5rem;">
                    <div class="team-card-head">
                        <h4>Team ${teamNum}</h4>
                        <span>${members.length} members</span>
                    </div>
                    
                    <div style="background: #f8fafc; padding: 0.65rem 0.85rem; border-left: 4px solid var(--indigo-600); margin-bottom: 1rem; border-radius: 4px; border: 1px solid var(--slate-200); border-left-width: 4px; text-align: left;">
                        <strong style="color: var(--slate-800); font-size: 0.85rem; display: block; margin-bottom: 0.15rem;">Mutual Overlap Work Window:</strong>
                        <span style="color: var(--indigo-700); font-size: 0.88rem; font-weight: 650;">${escapeHtml(teamOverlap)}</span>
                    </div>

                    ${members.map(member => `
                        <div class="team-member-row">
                            <div>
                                <strong>${escapeHtml(member.name)} ${member.is_lead ? '<span class="lead-badge">Team Lead</span>' : ''}</strong>
                                <small>${escapeHtml(member.roll_no || member.username)}</small>
                            </div>
                            <div class="team-actions">
                                <button class="icon-action" title="Make this student team lead" onclick="editTeam('${projectId}', 'leader', '${member.id}', '${teamNum}')">Make Lead</button>
                                <select onchange="editTeam('${projectId}', 'move', '${member.id}', this.value)">${options}</select>
                                <button class="icon-action danger" title="Remove" onclick="editTeam('${projectId}', 'remove', '${member.id}', '${teamNum}')">Remove</button>
                            </div>
                        </div>
                    `).join("")}
                </div>
            `;
        });

        eligibleStrip.innerHTML = eligible.length ? `
            <h4>Unassigned students (${eligible.length})</h4>
            ${eligible.map(student => `
                <div class="unassigned-student-row">
                    <div><strong>${escapeHtml(student.name)}</strong><small>${escapeHtml(student.college_id)} | ${escapeHtml(student.class)}</small></div>
                    <div class="team-actions">
                        <select id="reassign-team-${projectId}-${student.id}">${teamOptions || '<option value="1">Team 1</option>'}</select>
                        <button class="icon-action" onclick="editTeam('${projectId}', 'add', '${student.id}', fieldValue('reassign-team-${projectId}-${student.id}'))">Assign</button>
                    </div>
                </div>
            `).join("")}
        ` : `<p class="muted-text">No unassigned students for this project.</p>`;
    });
}

function editTeam(projectId, action, studentId, teamNumber) {
    fetch(`/api/faculty/project/${projectId}/team-edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, student_id: studentId, team_number: teamNumber })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) notifySync(data.message, "error");
        loadRosterPrintData(projectId);
        loadTeamCompletionGraph(projectId);
        loadFacultyProjectCompletionGraph();
    });
}

function loadStatusMatrix(projectId) {
    const container = document.getElementById(`status-matrix-${projectId}`);
    if (!container) return;
    fetch(`/api/faculty/project/${projectId}/status-matrix`)
    .then(res => res.json())
    .then(rows => {
        if (!rows.length) {
            container.innerHTML = `<p class="muted-text">No assigned students found for this project.</p>`;
            return;
        }
        container.innerHTML = rows.map(row => `
            <div class="student-status-card">
                <div class="status-head">
                    <div><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(row.college_id)} | ${escapeHtml(row.account_status)}</small></div>
                    <span>${escapeHtml(row.quiz_status)} | ${row.marks} marks</span>
                </div>
                ${row.answers.map(answer => `
                    <div class="answer-review">
                        <p><strong>${escapeHtml(answer.topic)}</strong>: ${escapeHtml(answer.question)}</p>
                        <blockquote>${escapeHtml(answer.answer || "No answer submitted")}</blockquote>
                        <label>Marks <input type="number" min="0" max="${answer.max_marks}" value="${answer.marks_awarded ?? ''}" onchange="gradeAnswer('${projectId}', '${row.id}', '${answer.flashcard_id}', this.value)"> / ${answer.max_marks}</label>
                    </div>
                `).join("")}
            </div>
        `).join("");
    });
}

function gradeAnswer(projectId, studentId, flashcardId, marks) {
    fetch(`/api/faculty/project/${projectId}/grade-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, flashcard_id: flashcardId, marks })
    });
}

function loadProjectMessages(projectId) {
    const panel = document.getElementById(`messages-panel-${projectId}`);
    if (!panel) return;
    fetch(`/api/project/${projectId}/messages?channel_type=team`)
    .then(res => res.json())
    .then(messages => {
        if (!Array.isArray(messages) || messages.length === 0) {
            panel.innerHTML = `<p class="muted-text">No team lead doubts have been posted yet.</p>`;
            return;
        }
        const grouped = messages.reduce((acc, message) => {
            const team = message.team_number || "Unassigned";
            if (!acc[team]) acc[team] = [];
            acc[team].push(message);
            return acc;
        }, {});
        panel.innerHTML = Object.entries(grouped).map(([teamNum, teamMessages]) => `
            <div class="message-composer team-message-thread">
                <h4>Team ${escapeHtml(teamNum)}</h4>
                <div class="message-list">${teamMessages.map(m => `<p><strong>${escapeHtml(m.sender)}</strong> <small>${escapeHtml(m.created_at)}</small><br>${escapeHtml(m.body)}</p>`).join("")}</div>
                <textarea id="message-body-${projectId}-${teamNum}" rows="2" placeholder="Reply to Team ${escapeHtml(teamNum)}"></textarea>
                <button class="btn primary-btn" onclick="sendProjectMessage('${projectId}', '${teamNum}')">Reply</button>
            </div>
        `).join("");
    });
}

function sendProjectMessage(projectId, teamNumber) {
    fetch(`/api/project/${projectId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            channel_type: 'team',
            team_number: teamNumber,
            body: fieldValue(`message-body-${projectId}-${teamNumber}`)
        })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) notifySync(data.message || data.error || "Message could not be sent.", "error");
        loadProjectMessages(projectId);
    });
}

function clearProjectMessages(projectId, teamNumber = "") {
    const params = new URLSearchParams({ channel_type: 'team' });
    if (teamNumber) params.set('team_number', teamNumber);

    fetch(`/api/project/${projectId}/messages?${params.toString()}`, { method: 'DELETE' })
    .then(res => res.json())
    .then(data => {
        notifySync(data.message || data.error || "Messages cleared.", data.success ? "success" : "error");
        loadProjectMessages(projectId);
    })
    .catch(() => notifySync("Unable to clear messages. Please try again.", "error"));
}

function triggerSystemPrintOperation() {
    window.print();
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.caps-only').forEach(field => {
        field.addEventListener('input', () => {
            field.value = field.value.toUpperCase();
        });
    });
});
