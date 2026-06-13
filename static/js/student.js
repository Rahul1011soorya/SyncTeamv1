/**
 * SyncTeam Workspace - Student Interaction Engine
 * Handles dynamic skill evaluation bars and visual time slot allocation blocks.
 */

let selectedScheduleBinaryArray = Array(24).fill(0); // Holds 24 hourly matrix slots

// 1. FETCH CRITERIA AND ASSEMBLE INTERACTIVE SLIDERS
function fetchDynamicProjectRequirements() {
    const projectId = document.getElementById('project-selector').value;
    const slidersStack = document.getElementById('dynamic-sliders-stack');
    const calendarGrid = document.getElementById('calendar-binary-grid');

    if (!slidersStack) return; // Prevent execution if not on the project sheet view page

    // Step A: Fetch and render skill competency capability bars
    fetch(`/api/project/${projectId}/skills`)
    .then(res => res.json())
    .then(skills => {
        slidersStack.innerHTML = "";
        if (skills.length === 0) {
            slidersStack.innerHTML = "<p class='muted-text'>No explicit capability criteria declared by faculty.</p>";
            return;
        }

        skills.forEach(skill => {
            slidersStack.innerHTML += `
                <div class="slider-container-box" style="background: var(--slate-50); padding: 1.25rem; border-radius: 8px; margin-bottom: 1.25rem; border: 1px solid var(--slate-200);">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.95rem; color: var(--slate-800);">
                        <span>${skill.name}</span>
                        <span>Score: <strong id="score-display-${skill.id}" style="color: var(--indigo-600);">5</strong> / 10</span>
                    </div>
                    <input type="range" class="competency-slider" data-skill-id="${skill.id}" min="1" max="10" value="5" 
                        style="width: 100%; margin-top: 0.75rem;" 
                        oninput="document.getElementById('score-display-${skill.id}').innerText = this.value">
                </div>
            `;
        });
    });

    // Step B: Construct the 24-Hour Clickable Visual Matrix Blocks
    if (calendarGrid) {
        calendarGrid.innerHTML = "";
        for (let hour = 0; hour < 24; hour++) {
            let displayHour = hour === 0 ? "12 AM" : hour === 12 ? "12 PM" : hour > 12 ? (hour - 12) + " PM" : hour + " AM";
            calendarGrid.innerHTML += `
                <div class="schedule-cell" id="hour-block-${hour}" onclick="toggleScheduleCell(${hour})" 
                     style="padding: 0.75rem; border: 1px solid var(--slate-200); text-align: center; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600; background: #e2e8f0; transition: all 0.15s ease; user-select: none;">
                    ${displayHour}
                </div>
            `;
        }
    }
}

// 2. TOGGLE CELL STATE INSIDE THE VISUAL MATRIX GRID
function toggleScheduleCell(hour) {
    const cell = document.getElementById(`hour-block-${hour}`);
    if (selectedScheduleBinaryArray[hour] === 0) {
        selectedScheduleBinaryArray[hour] = 1;
        cell.style.background = "var(--emerald-600)";
        cell.style.color = "#ffffff";
    } else {
        selectedScheduleBinaryArray[hour] = 0;
        cell.style.background = "#e2e8f0";
        cell.style.color = "initial";
    }
}

// 3. COMPILE DATA AND SUBMIT PERFORMANCE INTAKE SHEET
function dispatchStudentAssessment() {
    const projectId = document.getElementById('project-selector').value;
    
    const competenciesPayload = {};
    document.querySelectorAll('.competency-slider').forEach(slider => {
        const skillId = slider.getAttribute('data-skill-id');
        competenciesPayload[skillId] = slider.value;
    });

    fetch('/api/student/submit-assessment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: projectId,
            competencies: competenciesPayload,
            schedule: selectedScheduleBinaryArray
        })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        if (data.success) {
            window.location.href = '/student/dashboard';
        }
    });
}

function dispatchFlashcardAnswers() {
    const projectId = document.getElementById('project-selector').value;
    const answers = {};
    document.querySelectorAll('.student-flashcard-answer').forEach(field => {
        answers[field.getAttribute('data-flashcard-id')] = field.value.trim();
    });

    fetch('/api/student/submit-flashcards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, answers })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        if (data.success) window.location.reload();
    });
}

// 4. SUBMIT TEAM LEAD MILESTONE PROGRESS UPDATE
function dispatchMilestoneProgress(projectId, teamNumber) {
    const pct = document.getElementById('progress_percentage_slider').value;
    const summary = document.getElementById('progress_summary_text').value.trim();

    fetch('/api/student/update-progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: projectId,
            team_number: teamNumber,
            completion_percentage: pct,
            status_summary: summary
        })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        if (data.success) window.location.reload();
    });
}
