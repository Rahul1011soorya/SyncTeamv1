import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from db import db, Institution, CrossTenantAccessRequest, User, Project, GlobalSkill, ProjectSkillRequirement, StudentCompetency, Schedule, TeamAssignment, TeamProgress, DoubtTicket
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'syncteam_academic_isolated_multi_tenant_secure_matrix_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///syncteam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ==========================================
# MULTI-TENANT SYSTEM INITIALIZATION ENGINE
# ==========================================

with app.app_context():
    db.create_all()
    
    # 1. Seed the Core Institution Workspace Domain
    inst_code = 'MBCET'
    if not Institution.query.filter_by(institution_code=inst_code).first():
        db.session.add(Institution(
            institution_code=inst_code,
            name='Mar Baselios College of Engineering and Technology',
            address='Nalanchira, Thiruvananthapuram, Kerala',
            roll_no_format='B24CS12XX',
            faculty_id_format='MBCET-FAC-XX',
            batch_format='01',
            class_format='CS2',
            academic_year_format='2024-2028',
            semester_format='S4',
            subject_format='CSXXX',
            stream_format='B.Tech'
        ))
        db.session.commit()

    # 2. Seed Dedicated MBCET Workspace Admin Account
    if not User.query.filter_by(username='mbcet_admin').first():
        db.session.add(User(
            username='mbcet_admin',
            password_hash='admin@mbcet',
            role='admin',
            home_institution_code=inst_code,
            real_name='MBCET Central Admin Office'
        ))

    # 3. Seed Sample Faculty Members
    sample_faculties = [
        {"username": "faculty1", "password": "faculty@1", "name": "Prof. Afrin Shamnath", "sub": "Data Structures"},
        {"username": "faculty2", "password": "faculty@2", "name": "Prof. Karthik Manoj", "sub": "Operating Systems"},
        {"username": "faculty3", "password": "faculty@3", "name": "Prof. Arya R Nair", "sub": "Design Engineering"}
    ]
    
    for fac in sample_faculties:
        if not User.query.filter_by(username=fac["username"]).first():
            db.session.add(User(
                username=fac["username"],
                password_hash=fac["password"],
                role='faculty',
                home_institution_code=inst_code,
                real_name=fac["name"],
                stream='B.Tech',
                class_name='CS2',
                batch='01',
                semester='S4',
                academic_year='2024-2028',
                faculty_id=f"MBCET-FAC-{fac['username'][-1]}",
                subject_specialization=fac["sub"]
            ))

    # 4. Programmatic Generation: Seed 30 Sequential Student Profiles
    for i in range(1, 31):
        username_handle = f"student{i}"
        password_handle = f"student@{i}"
        
        if not User.query.filter_by(username=username_handle).first():
            db.session.add(User(
                username=username_handle,
                password_hash=password_handle,
                role='student',
                home_institution_code=inst_code,
                real_name=f"Roster Student Unit {i:02d}",
                stream='B.Tech',
                class_name='CS2',
                batch='01',
                semester='S4',
                academic_year='2024-2028',
                student_roll_no=f"B24CS12{i:02d}"
            ))
            
    # Pre-populate global baseline dictionary components
    baseline_skills = ['Frontend Design', 'Backend Architecture', 'Database Optimization', 'Technical Documentation']
    for skill in baseline_skills:
        if not GlobalSkill.query.filter_by(skill_name=skill).first():
            db.session.add(GlobalSkill(skill_name=skill))
            
    db.session.commit()

# ==========================================
# CENTRALIZED COMPLIANCE & VIEW GATEWAYS
# ==========================================

@app.route('/')
def role_selection():
    institutions = Institution.query.all()
    return render_template('role_selection.html', institutions=institutions)

@app.route('/portal/<role>')
def login_page(role):
    target_inst = request.args.get('inst_code', 'MBCET')
    institution_profile = Institution.query.filter_by(institution_code=target_inst).first()
    return render_template('login.html', role=role, inst_code=target_inst, institution=institution_profile)

@app.route('/signup/<role>')
def signup_page(role):
    target_inst = request.args.get('inst_code', 'MBCET')
    institution_profile = Institution.query.filter_by(institution_code=target_inst).first()
    return render_template('signup.html', role=role, inst_code=target_inst, institution=institution_profile)

@app.route('/faculty/dashboard')
def faculty_dashboard():
    if session.get('role') != 'faculty': return redirect(url_for('role_selection'))
    projects = Project.query.filter_by(institution_code=session['institution_code']).order_by(Project.created_at.desc()).all()
    return render_template('faculty_dashboard.html', projects=projects)

@app.route('/faculty/create-project')
def faculty_create_project():
    if session.get('role') != 'faculty': return redirect(url_for('role_selection'))
    skills = GlobalSkill.query.all()
    return render_template('faculty_create_project.html', skills=skills)

@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student': return redirect(url_for('role_selection'))
    assigned_projects = Project.query.filter_by(institution_code=session['institution_code']).order_by(Project.created_at.asc()).all()
    return render_template('student_dashboard.html', projects=assigned_projects)

@app.route('/student/project/<int:project_id>')
def student_project_view(project_id):
    if session.get('role') != 'student': return redirect(url_for('role_selection'))
    project = Project.query.get_or_404(project_id)
    return render_template('student_project_view.html', project=project)

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('role_selection'))
    user_count = User.query.filter_by(home_institution_code=session['institution_code']).count()
    project_count = Project.query.filter_by(institution_code=session['institution_code']).count()
    return render_template('admin_dashboard.html', user_count=user_count, project_count=project_count)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('role_selection'))

# ==========================================
# SECURE SYSTEM TRANSACTION APIs
# ==========================================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    active_inst_context = data.get('inst_code')
    
    user = User.query.filter_by(username=username, password_hash=password, role=role).first()
    if not user:
        return jsonify({"success": False, "message": "Authentication tokens rejected."})
        
    if user.home_institution_code != active_inst_context:
        has_approval = CrossTenantAccessRequest.query.filter_by(
            user_id=user.id, target_institution_code=active_inst_context, status='APPROVED'
        ).first()
        if not has_approval:
            return jsonify({
                "success": False, 
                "message": f"Tenant Access Violation: Account belongs to {user.home_institution_code}."
            })
            
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['real_name'] = user.real_name
    session['institution_code'] = active_inst_context
    return jsonify({"success": True})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({"success": False, "message": "Username already taken."})
        
    new_user = User(
        username=data.get('username'),
        password_hash=data.get('password'),
        role=data.get('role'),
        home_institution_code=data.get('inst_code'),
        real_name=data.get('real_name'),
        stream=data.get('stream'),
        class_name=data.get('class_name'),
        batch=data.get('batch'),
        semester=data.get('semester'),
        academic_year=data.get('academic_year'),
        faculty_id=data.get('faculty_id') if data.get('role') == 'faculty' else None,
        student_roll_no=data.get('student_roll_no') if data.get('role') == 'student' else None,
        subject_specialization=data.get('subject') if data.get('role') == 'faculty' else None
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": "Registration approved under secure tenant isolation!"})

@app.route('/api/admin/configure-formats', methods=['POST'])
def configure_formats():
    if session.get('role') != 'admin': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    inst = Institution.query.filter_by(institution_code=session['institution_code']).first()
    if inst:
        inst.roll_no_format = data.get('roll_format', inst.roll_no_format)
        inst.faculty_id_format = data.get('faculty_format', inst.faculty_id_format)
        inst.batch_format = data.get('batch_format', inst.batch_format)
        inst.class_format = data.get('class_format', inst.class_format)
        inst.academic_year_format = data.get('year_format', inst.academic_year_format)
        inst.semester_format = data.get('semester_format', inst.semester_format)
        db.session.commit()
        return jsonify({"success": True, "message": "Formatting templates locked!"})
    return jsonify({"success": False, "message": "Institution profile missing."})

@app.route('/api/reports/discover-students', methods=['GET'])
def discover_students():
    if session.get('role') not in ['admin', 'faculty']: return jsonify({"error": "Unauthorized"}), 403
    query = User.query.filter_by(role='student', home_institution_code=session['institution_code'])
    
    if request.args.get('stream'): query = query.filter_by(stream=request.args.get('stream'))
    if request.args.get('class_name'): query = query.filter_by(class_name=request.args.get('class_name'))
    if request.args.get('batch'): query = query.filter_by(batch=request.args.get('batch'))
    if request.args.get('semester'): query = query.filter_by(semester=request.args.get('semester'))
    if request.args.get('academic_year'): query = query.filter_by(academic_year=request.args.get('academic_year'))
    
    students = query.all()
    return jsonify([{
        "name": s.real_name, "roll_no": s.student_roll_no, "class": s.class_name,
        "batch": s.batch, "semester": s.semester, "stream": s.stream, "year": s.academic_year
    } for s in students])

@app.route('/api/project/deploy', methods=['POST'])
def api_deploy_project():
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    new_p = Project(
        institution_code=session['institution_code'],
        project_name=data['name'],
        description=data['description'],
        deadline=data['deadline'],
        team_size=int(data['team_size']),
        class_batch=data['batch']
    )
    db.session.add(new_p)
    db.session.commit()
    
    for s_name in data['skills']:
        s_name_clean = s_name.strip()
        if not s_name_clean: continue
        skill_node = GlobalSkill.query.filter_by(skill_name=s_name_clean).first()
        if not skill_node:
            skill_node = GlobalSkill(skill_name=s_name_clean)
            db.session.add(skill_node)
            db.session.commit()
        db.session.add(ProjectSkillRequirement(project_id=new_p.id, skill_id=skill_node.id))
        
    db.session.commit()
    return jsonify({"success": True, "message": "Framework deployed to active tenant pool!"})

@app.route('/api/project/<int:project_id>/skills')
def api_project_skills(project_id):
    linked_requirements = ProjectSkillRequirement.query.filter_by(project_id=project_id).all()
    compiled_skills_payload = []
    for req in linked_requirements:
        skill_entity = GlobalSkill.query.get(req.skill_id)
        if skill_entity:
            compiled_skills_payload.append({"id": skill_entity.id, "name": skill_entity.skill_name})
    return jsonify(compiled_skills_payload)

@app.route('/api/student/submit-assessment', methods=['POST'])
def api_submit_assessment():
    if session.get('role') != 'student': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    uid = session['user_id']
    pid = int(data['project_id'])
    
    for s_id, score in data['competencies'].items():
        existing = StudentCompetency.query.filter_by(user_id=uid, project_id=pid, skill_id=int(s_id)).first()
        if existing: existing.score = int(score)
        else: db.session.add(StudentCompetency(user_id=uid, project_id=pid, skill_id=int(s_id), score=int(score)))
            
    schedule_string = ",".join(map(str, data['schedule']))
    existing_sched = Schedule.query.filter_by(user_id=uid, project_id=pid).first()
    if existing_sched: existing_sched.availability_matrix = schedule_string
    else: db.session.add(Schedule(user_id=uid, project_id=pid, availability_matrix=schedule_string))
    
    db.session.commit()
    return jsonify({"success": True, "message": "Form metrics locked inside tenant records!"})

# ==========================================
# TEAM MANAGEMENT & ALGORITHM CLUSTERS
# ==========================================

@app.route('/api/faculty/assign-team-lead', methods=['POST'])
def assign_team_lead():
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    pid = data.get('project_id')
    t_num = data.get('team_number')
    target_student_id = User.query.filter_by(username=data.get('student_id')).first().id
    
    TeamAssignment.query.filter_by(project_id=pid, team_number=t_num).update({"is_team_lead": False})
    assigned_member = TeamAssignment.query.filter_by(project_id=pid, team_number=t_num, student_id=target_student_id).first()
    if assigned_member:
        assigned_member.is_team_lead = True
        if not TeamProgress.query.filter_by(project_id=pid, team_number=t_num).first():
            db.session.add(TeamProgress(project_id=pid, team_number=t_num, completion_percentage=0, status_summary="Awaiting initial update from Team Lead."))
        db.session.commit()
        return jsonify({"success": True, "message": "Team Lead nominated successfully!"})
    return jsonify({"success": False, "message": "Roster mapping parameter mismatch."})

@app.route('/api/student/update-progress', methods=['POST'])
def update_progress():
    if session.get('role') != 'student': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    pid = data.get('project_id')
    t_num = data.get('team_number')
    pct = int(data.get('completion_percentage', 0))
    summary = data.get('status_summary')
    
    lead_check = TeamAssignment.query.filter_by(project_id=pid, team_number=t_num, student_id=session['user_id'], is_team_lead=True).first()
    if not lead_check:
        return jsonify({"success": False, "message": "Operation Restricted: You must be the assigned Team Lead to edit milestones."})
        
    prog = TeamProgress.query.filter_by(project_id=pid, team_number=t_num).first()
    if prog:
        prog.completion_percentage = pct
        prog.status_summary = summary
        db.session.commit()
        return jsonify({"success": True, "message": "Milestones saved successfully!"})
    return jsonify({"success": False, "message": "Alignment lookup failure."})

@app.route('/api/faculty/compliance-report/<int:project_id>', methods=['GET'])
def compliance_report(project_id):
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    participated_subquery = db.session.query(StudentCompetency.user_id).filter(StudentCompetency.project_id == project_id).subquery()
    outstanding_students = User.query.filter_by(role='student', home_institution_code=session['institution_code']).filter(~User.id.in_(participated_subquery)).all()
    return jsonify([{"id": s.id, "name": s.real_name, "roll_no": s.student_roll_no, "class": s.class_name, "batch": s.batch} for s in outstanding_students])

@app.route('/api/project/<int:project_id>/generate-teams', methods=['POST'])
def generate_teams(project_id):
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    project = Project.query.get_or_404(project_id)
    target_size = project.team_size
    
    competent_roster = db.session.query(User.id, db.func.sum(StudentCompetency.score).label('total_weight')).join(
        StudentCompetency, User.id == StudentCompetency.user_id
    ).filter(StudentCompetency.project_id == project_id).group_by(User.id).order_by(db.desc('total_weight')).all()
    
    if not competent_roster:
        return jsonify({"success": False, "message": "Matchmaking halted: No student metrics recorded yet."})
        
    TeamAssignment.query.filter_by(project_id=project_id).delete()
    total_count = len(competent_roster)
    num_teams = max(1, total_count // target_size)
    teams_accumulator = [[] for _ in range(num_teams)]
    
    for rank_idx, student in enumerate(competent_roster):
        wave_cycle = rank_idx // num_teams
        target_bucket = rank_idx % num_teams
        if wave_cycle % 2 != 0:
            target_bucket = (num_teams - 1) - target_bucket
        teams_accumulator[target_bucket].append(student.id)
        
    for team_idx, members in enumerate(teams_accumulator):
        t_num = team_idx + 1
        for m_id in members:
            db.session.add(TeamAssignment(project_id=project_id, student_id=m_id, team_number=t_num))
            
    db.session.commit()
    return jsonify({"success": True, "message": f"Optimization engine complete! Formed {num_teams} balanced clusters."})

@app.route('/api/project/<int:project_id>/roster-report')
def get_roster_report(project_id):
    records = db.session.query(TeamAssignment.team_number, User.real_name, User.username, TeamAssignment.is_team_lead).join(
        User, TeamAssignment.student_id == User.id
    ).filter(TeamAssignment.project_id == project_id).order_by(TeamAssignment.team_number.asc()).all()
    
    report_dictionary = {}
    for t_num, r_name, u_name, is_lead in records:
        if t_num not in report_dictionary: report_dictionary[t_num] = []
        # Explicit append adding custom leading check icons if student holds an active lead token row property
        display_name = f"👑 {r_name} (Team Lead)" if is_lead else r_name
        report_dictionary[t_num].append({"name": display_name, "username": u_name})
    return jsonify(report_dictionary)


# ==========================================
# INSTITUTION COHORT ONBOARDING GATEWAYS
# ==========================================

@app.route('/register-institution')
def register_institution_page():
    return render_template('register_institution.html')

@app.route('/api/institution/register', methods=['POST'])
def api_register_institution():
    data = request.json
    code = data.get('code', '').strip().upper()
    name = data.get('name', '').strip()
    address = data.get('address', '').strip()
    admin_user = data.get('admin_username', '').strip()
    admin_pass = data.get('admin_password', '').strip()

    if not code or not name or not admin_user or not admin_pass:
        return jsonify({"success": False, "message": "All database fields are mandatory."})

    if Institution.query.filter_by(institution_code=code).first():
        return jsonify({"success": False, "message": "This institution code is already taken."})
        
    if User.query.filter_by(username=admin_user).first():
        return jsonify({"success": False, "message": "Admin username already registered globally."})

    # Initialize New Isolated Tenancy Entry Row
    new_inst = Institution(
        institution_code=code,
        name=name,
        address=address,
        roll_no_format='FORMAT-YY-XXXX',
        faculty_id_format='FAC-XX-XXXX',
        batch_format='Batch XX',
        class_format='DIV-X',
        academic_year_format='202X-202X',
        semester_format='SX'
    )
    db.session.add(new_inst)
    
    # Bind Initializing Super Admin Entity to this Specific Tenant Code
    new_admin = User(
        username=admin_user,
        password_hash=admin_pass,
        role='admin',
        home_institution_code=code,
        real_name=f"{name} Admin Node Office"
    )
    db.session.add(new_admin)
    db.session.commit()

    return jsonify({"success": True, "message": "New workspace successfully compiled and isolated!"})

if __name__ == '__main__':
    app.run(debug=True)