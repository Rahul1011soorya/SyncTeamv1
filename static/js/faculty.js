const selectedCohorts = [];

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
        alert("Fill the project title, brief, deadline, and at least one cohort.");
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
        alert(data.message);
        if (data.success) window.location.href = '/faculty/dashboard';
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
        alert(data.message);
        if (data.success) loadRosterPrintData(projectId);
    });
}

function loadRosterPrintData(projectId) {
    Promise.all([
        fetch(`/api/project/${projectId}/roster-report`).then(res => res.json()),
        fetch(`/api/project/${projectId}/eligible-students`).then(res => res.json())
    ]).then(([teams, eligible]) => {
        const output = document.getElementById(`teams-allocation-view-${projectId}`);
        const eligibleStrip = document.getElementById(`eligible-students-${projectId}`);
        if (!output) return;
        output.innerHTML = "";

        if (Object.keys(teams).length === 0) {
            output.innerHTML = `<p class="muted-text">No team allocation exists yet.</p>`;
        }

        Object.entries(teams).forEach(([teamNum, members]) => {
            const options = Object.keys(teams).map(num => `<option value="${num}">Team ${num}</option>`).join("");
            output.innerHTML += `
                <div class="team-card">
                    <div class="team-card-head"><h4>Team ${teamNum}</h4><span>${members.length} members</span></div>
                    ${members.map(member => `
                        <div class="team-member-row">
                            <div><strong>${member.is_lead ? "Crown " : ""}${escapeHtml(member.name)}</strong><small>${escapeHtml(member.roll_no || member.username)}</small></div>
                            <div class="team-actions">
                                <button class="icon-action" title="Make leader" onclick="editTeam('${projectId}', 'leader', '${member.id}', '${teamNum}')">Crown</button>
                                <select onchange="editTeam('${projectId}', 'move', '${member.id}', this.value)">${options}</select>
                                <button class="icon-action danger" title="Remove" onclick="editTeam('${projectId}', 'remove', '${member.id}', '${teamNum}')">Remove</button>
                            </div>
                        </div>
                    `).join("")}
                </div>
            `;
        });

        eligibleStrip.innerHTML = eligible.length ? `<h4>Add unassigned students</h4>` + eligible.map(student => `
            <button class="chip-btn" onclick="editTeam('${projectId}', 'add', '${student.id}', '1')">${escapeHtml(student.name)} (${escapeHtml(student.college_id)})</button>
        `).join("") : "";
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
        if (!data.success) alert(data.message);
        loadRosterPrintData(projectId);
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
    fetch(`/api/project/${projectId}/messages?channel_type=private`)
    .then(res => res.json())
    .then(messages => {
        panel.innerHTML = `
            <div class="message-composer">
                <h4>Private doubts</h4>
                <div class="message-list">${messages.map(m => `<p><strong>${escapeHtml(m.sender)}</strong> <small>${escapeHtml(m.created_at)}</small><br>${escapeHtml(m.body)}</p>`).join("") || "No messages yet."}</div>
                <textarea id="message-body-${projectId}" rows="2" placeholder="Reply or post a project note"></textarea>
                <button class="btn primary-btn" onclick="sendProjectMessage('${projectId}')">Send</button>
            </div>
        `;
    });
}

function sendProjectMessage(projectId) {
    fetch(`/api/project/${projectId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_type: 'private', body: fieldValue(`message-body-${projectId}`) })
    })
    .then(res => res.json())
    .then(() => loadProjectMessages(projectId));
}

function triggerSystemPrintOperation() {
    window.print();
}
