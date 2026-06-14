import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from db import db, Institution, CrossTenantAccessRequest, User, Project, ProjectCohortAssignment, ProjectFlashcard, StudentFlashcardAnswer, GlobalSkill, ProjectSkillRequirement, StudentCompetency, Schedule, TeamAssignment, TeamProgress, DoubtTicket, CommunicationMessage
from datetime import datetime
from sqlalchemy import inspect, or_, and_, text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'syncteam_academic_isolated_multi_tenant_secure_matrix_key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SYNCTEAM_DATABASE_URI', 'sqlite:///syncteam.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

HASH_PREFIXES = ("scrypt:", "pbkdf2:", "argon2:")

def secure_password(password):
    return generate_password_hash(password)

def is_hashed_password(value):
    return bool(value) and value.startswith(HASH_PREFIXES)

def verify_password(stored_value, candidate):
    if not stored_value or stored_value == "UNCLAIMED":
        return False
    if is_hashed_password(stored_value):
        return check_password_hash(stored_value, candidate)
    return stored_value == candidate

# ==========================================
# MULTI-TENANT SYSTEM INITIALIZATION ENGINE
# ==========================================

with app.app_context():
    db.create_all()

    # Lightweight compatibility patch for existing SQLite databases.
    users_columns = [col["name"] for col in inspect(db.engine).get_columns("users")]
    if "is_approved" not in users_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT 1"))
        db.session.commit()
    if "age" not in users_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN age INTEGER"))
        db.session.commit()
    if "enrollment_year" not in users_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN enrollment_year VARCHAR(10)"))
        db.session.commit()
    if "account_claimed" not in users_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN account_claimed BOOLEAN NOT NULL DEFAULT 1"))
        db.session.commit()
    
    # 1. Seed the Core Institution Workspace Domain
    inst_code = 'MBCET'
    if not Institution.query.filter_by(institution_code=inst_code).first():
        db.session.add(Institution(
            institution_code=inst_code,
            name='Mar Baselios College of Engineering and Technology',
            address='Nalanchira, Thiruvananthapuram, Kerala',
            roll_no_format='B24CS1235',
            faculty_id_format='MBTCSA13',
            batch_format='Class 1 / Class 2',
            class_format='Department Class 1 / Department Class 2',
            academic_year_format='2024-2028',
            semester_format='S4',
            subject_format='Department Subject',
            stream_format='Computer Science / Electronics Communication / Electrical Engg / Civil Engg / Mechanical Engg'
        ))
        db.session.commit()

    # 2. Seed Dedicated MBCET Workspace Admin Account
    if not User.query.filter_by(username='mbcet_admin').first():
        db.session.add(User(
            username='mbcet_admin',
            password_hash=secure_password('admin@mbcet'),
            role='admin',
            home_institution_code=inst_code,
            real_name='MBCET Central Admin Office'
        ))

    # 3. Seed MBCET-wide static enrollment data for the 2024-2028 batch.
    department_catalog = [
        {"code": "CS", "core": "1", "name": "COMPUTER SCIENCE", "subjects": ["DATA STRUCTURES", "DATABASE SYSTEMS", "WEB ENGINEERING", "AI FOUNDATIONS"]},
        {"code": "EC", "core": "1", "name": "ELECTRONICS COMMUNICATION", "subjects": ["DIGITAL ELECTRONICS", "SIGNALS AND SYSTEMS", "VLSI DESIGN", "COMMUNICATION SYSTEMS"]},
        {"code": "EE", "core": "1", "name": "ELECTRICAL ENGG", "subjects": ["POWER SYSTEMS", "ELECTRICAL MACHINES", "CONTROL SYSTEMS", "CIRCUIT THEORY"]},
        {"code": "CE", "core": "1", "name": "CIVIL ENGG", "subjects": ["STRUCTURAL ANALYSIS", "SURVEYING", "GEOTECHNICAL ENGINEERING", "CONCRETE TECHNOLOGY"]},
        {"code": "ME", "core": "1", "name": "MECHANICAL ENGG", "subjects": ["THERMODYNAMICS", "FLUID MECHANICS", "MACHINE DESIGN", "MANUFACTURING PROCESS"]}
    ]

    first_names = [
        "AARON", "ABHAY", "ADITHYA", "AKHIL", "AMAN", "AMRITHA", "ANAND", "ANJALI", "ANNA", "ARJUN",
        "ARYA", "ATHIRA", "DEVIKA", "DIYA", "GOKUL", "HARITHA", "JEEVAN", "KARTHIK", "LAKSHMI", "MEERA",
        "NANDANA", "NEHA", "NITHIN", "PRIYA", "RAHUL"
    ]
    last_names = [
        "ALEX", "ANTONY", "BABU", "CHANDRAN", "DAS", "GEORGE", "JOSE", "KOSHY", "KUMAR", "MATHEW",
        "MENON", "NAIR", "PAUL", "PILLAI", "RAJAN", "RAVI", "ROY", "SANKAR", "THOMAS", "VARMA"
    ]

    # Remove the earlier 30-student demo roster so the college list becomes the source of truth.
    demo_students = User.query.filter(
        User.role == 'student',
        User.home_institution_code == inst_code,
        User.real_name.like('Roster Student Unit%')
    ).all()
    for demo_student in demo_students:
        db.session.delete(demo_student)

    demo_faculties = User.query.filter(
        User.role == 'faculty',
        User.home_institution_code == inst_code,
        User.username.in_(['faculty1', 'faculty2', 'faculty3'])
    ).all()
    for demo_faculty in demo_faculties:
        db.session.delete(demo_faculty)

    for dept_index, dept in enumerate(department_catalog):
        for class_number in [1, 2]:
            for roll_number in range(1, 51):
                name_index = ((dept_index * 100) + ((class_number - 1) * 50) + roll_number - 1) % (len(first_names) * len(last_names))
                first = first_names[name_index % len(first_names)]
                last = last_names[(name_index // len(first_names)) % len(last_names)]
                student_id = f"B24{dept['code']}{dept['core']}{class_number}{roll_number:02d}"

                if not User.query.filter_by(student_roll_no=student_id).first():
                    db.session.add(User(
                        username=f"enroll_{student_id.lower()}",
                        password_hash='UNCLAIMED',
                        role='student',
                        home_institution_code=inst_code,
                        real_name=f"{first} {last}",
                        stream=dept["name"],
                        class_name=f"{dept['code']} CLASS {class_number}",
                        batch=str(class_number),
                        semester='S1',
                        academic_year='2024-2028',
                        age=18 + (roll_number % 3),
                        enrollment_year='2024',
                        student_roll_no=student_id,
                        is_approved=True,
                        account_claimed=False
                    ))

                enrolled_student = User.query.filter_by(student_roll_no=student_id, role='student').first()
                if enrolled_student and (
                    enrolled_student.username == student_id.lower()
                    or enrolled_student.username.startswith('student')
                    or enrolled_student.password_hash.startswith(student_id.lower())
                ):
                    enrolled_student.username = f"enroll_{student_id.lower()}"
                    enrolled_student.password_hash = 'UNCLAIMED'
                    enrolled_student.account_claimed = False

        for teacher_index, subject in enumerate(dept["subjects"], start=1):
            faculty_id = f"MBT{dept['code']}A{teacher_index + (dept_index * 10):02d}"
            if not User.query.filter_by(faculty_id=faculty_id).first():
                db.session.add(User(
                    username=faculty_id.lower(),
                    password_hash=secure_password(f"{faculty_id.lower()}@2024"),
                    role='faculty',
                    is_approved=True,
                    home_institution_code=inst_code,
                    real_name=f"PROF {first_names[(dept_index * 4 + teacher_index) % len(first_names)]} {last_names[dept_index]}",
                    stream=dept["name"],
                    class_name=f"{dept['code']} FACULTY",
                    batch='ALL',
                    semester='S1',
                    academic_year='2024-2028',
                    age=32 + teacher_index + dept_index,
                    enrollment_year='2024',
                    faculty_id=faculty_id,
                    subject_specialization=subject,
                    account_claimed=True
                ))
            
    # Pre-populate global baseline dictionary components
    baseline_skills = ['Frontend Design', 'Backend Architecture', 'Database Optimization', 'Technical Documentation']
    for skill in baseline_skills:
        if not GlobalSkill.query.filter_by(skill_name=skill).first():
            db.session.add(GlobalSkill(skill_name=skill))

    # Upgrade legacy plaintext passwords in-place. UNCLAIMED seeded student rows are not login credentials.
    for user in User.query.all():
        if user.password_hash and user.password_hash != "UNCLAIMED" and not is_hashed_password(user.password_hash):
            user.password_hash = secure_password(user.password_hash)
            
    db.session.commit()

# ==========================================
# CENTRALIZED COMPLIANCE & VIEW GATEWAYS
# ==========================================

@app.route('/')
def role_selection():
    return render_template('role_selection.html')

@app.route('/portal/<role>')
def login_page(role):
    target_inst = 'MBCET'
    institution_profile = Institution.query.filter_by(institution_code=target_inst).first()
    return render_template('login.html', role=role, inst_code=target_inst, institution=institution_profile)

@app.route('/signup/<role>')
def signup_page(role):
    target_inst = 'MBCET'
    institution_profile = Institution.query.filter_by(institution_code=target_inst).first()
    return render_template('signup.html', role=role, inst_code=target_inst, institution=institution_profile)

@app.route('/faculty/dashboard')
def faculty_dashboard():
    if session.get('role') != 'faculty': return redirect(url_for('role_selection'))
    projects = Project.query.filter_by(institution_code=session['institution_code']).order_by(Project.created_at.desc()).all()
    students = User.query.filter_by(role='student', home_institution_code=session['institution_code']).all()
    cohort_options = {
        "years": sorted({s.academic_year for s in students if s.academic_year}),
        "departments": sorted({s.stream for s in students if s.stream}),
        "classes": sorted({s.class_name for s in students if s.class_name})
    }
    stats = {
        "projects": len(projects),
        "students": len(students),
        "teams": TeamAssignment.query.join(Project, TeamAssignment.project_id == Project.id).filter(Project.institution_code == session['institution_code']).count(),
        "messages": CommunicationMessage.query.join(Project, CommunicationMessage.project_id == Project.id).filter(Project.institution_code == session['institution_code']).count()
    }
    return render_template('faculty_dashboard.html', projects=projects, cohort_options=cohort_options, stats=stats)

@app.route('/faculty/create-project')
def faculty_create_project():
    if session.get('role') != 'faculty': return redirect(url_for('role_selection'))
    skills = GlobalSkill.query.all()
    students = User.query.filter_by(role='student', home_institution_code=session['institution_code']).all()
    cohort_options = {
        "years": sorted({s.academic_year for s in students if s.academic_year}),
        "departments": sorted({s.stream for s in students if s.stream}),
        "classes": sorted({s.class_name for s in students if s.class_name})
    }
    return render_template('faculty_create_project.html', skills=skills, cohort_options=cohort_options)

@app.route('/faculty/project/<int:project_id>')
def faculty_project_detail(project_id):
    if session.get('role') != 'faculty': return redirect(url_for('role_selection'))
    project = Project.query.filter_by(id=project_id, institution_code=session['institution_code']).first_or_404()
    return render_template('faculty_project_detail.html', project=project)

@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student': return redirect(url_for('role_selection'))
    student = User.query.get(session['user_id'])
    assigned_project_ids = db.session.query(ProjectCohortAssignment.project_id).filter(
        ProjectCohortAssignment.academic_year == student.academic_year,
        ProjectCohortAssignment.department == student.stream,
        ProjectCohortAssignment.class_name == student.class_name
    ).scalar_subquery()
    assigned_projects = Project.query.filter(
        Project.institution_code == session['institution_code'],
        Project.id.in_(assigned_project_ids)
    ).order_by(Project.created_at.asc()).all()
    return render_template('student_dashboard.html', projects=assigned_projects)

@app.route('/student/project/<int:project_id>')
def student_project_view(project_id):
    if session.get('role') != 'student': return redirect(url_for('role_selection'))
    project = Project.query.get_or_404(project_id)
    if not student_can_access_project(session['user_id'], project_id):
        return redirect(url_for('student_dashboard'))
    flashcards = ProjectFlashcard.query.filter_by(project_id=project_id).order_by(ProjectFlashcard.id.asc()).all()
    answers = StudentFlashcardAnswer.query.filter_by(project_id=project_id, student_id=session['user_id']).all()
    answer_map = {a.flashcard_id: a for a in answers}
    team_assignment = TeamAssignment.query.filter_by(project_id=project_id, student_id=session['user_id']).first()
    team_progress = None
    if team_assignment:
        team_progress = TeamProgress.query.filter_by(
            project_id=project_id,
            team_number=team_assignment.team_number
        ).first()
    return render_template(
        'student_project_view.html',
        project=project,
        flashcards=flashcards,
        answer_map=answer_map,
        team_assignment=team_assignment,
        team_progress=team_progress
    )

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('role_selection'))
    user_count = User.query.filter_by(home_institution_code=session['institution_code']).count()
    project_count = Project.query.filter_by(institution_code=session['institution_code']).count()
    pending_faculty = User.query.filter_by(
        role='faculty',
        home_institution_code=session['institution_code'],
        is_approved=False
    ).order_by(User.real_name.asc()).all()
    return render_template(
        'admin_dashboard.html',
        user_count=user_count,
        project_count=project_count,
        pending_faculty=pending_faculty
    )

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
    
    user = User.query.filter_by(username=username, role=role).first()
    if not user or not verify_password(user.password_hash, password):
        return jsonify({"success": False, "message": "Authentication tokens rejected."})

    if user.role == 'student' and not user.account_claimed:
        return jsonify({
            "success": False,
            "message": "Student account is not registered yet. Please complete student registration first."
        })

    if user.role == 'faculty' and not user.is_approved:
        return jsonify({
            "success": False,
            "message": "Faculty access is pending admin approval. Please contact your institution admin."
        })
        
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
    role = data.get('role')
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."})

    if role == 'student':
        student_name = data.get('real_name', '').strip().upper()
        student_id = data.get('student_roll_no', '').strip().upper()

        if not student_name or not student_id:
            return jsonify({"success": False, "message": "University record name and student ID are required."})

        enrolled_student = User.query.filter_by(
            role='student',
            home_institution_code=data.get('inst_code'),
            real_name=student_name,
            student_roll_no=student_id
        ).first()

        if not enrolled_student:
            return jsonify({"success": False, "message": "Enrollment match failed. Name and Student ID must match university records."})

        if enrolled_student.account_claimed:
            return jsonify({"success": False, "message": "This student enrollment has already created an account."})

        if User.query.filter(User.username == username, User.id != enrolled_student.id).first():
            return jsonify({"success": False, "message": "Username already taken."})

        enrolled_student.username = username
        enrolled_student.password_hash = secure_password(password)
        enrolled_student.account_claimed = True
        enrolled_student.is_approved = True
        db.session.commit()
        return jsonify({"success": True, "message": "Student account created from verified university enrollment records."})

    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username already taken."})

    if role == 'faculty':
        faculty_name = data.get('real_name', '').strip().upper()
        teacher_id = data.get('faculty_id', '').strip().upper()

        if not faculty_name or not teacher_id:
            return jsonify({"success": False, "message": "Official record name and Teacher ID are required."})
        
    new_user = User(
        username=username,
        password_hash=secure_password(password),
        role=role,
        home_institution_code=data.get('inst_code'),
        real_name=data.get('real_name', '').strip().upper(),
        stream=data.get('stream'),
        class_name=data.get('class_name'),
        batch=data.get('batch'),
        semester=data.get('semester'),
        academic_year=data.get('academic_year'),
        faculty_id=data.get('faculty_id', '').strip().upper() if role == 'faculty' else None,
        student_roll_no=None,
        subject_specialization=data.get('subject') if role == 'faculty' else None,
        is_approved=False if role == 'faculty' else True,
        account_claimed=True
    )
    db.session.add(new_user)
    db.session.commit()
    if role == 'faculty':
        return jsonify({"success": True, "message": "Faculty registration submitted. You will be allowed after admin authentication."})
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

def apply_department_filter(query, department):
    if not department:
        return query

    department_tokens = {
        "Computer Science": ["Computer Science", "COMPUTER SCIENCE", "CS", "CSE"],
        "Mechanical": ["Mechanical", "MECHANICAL ENGG", "ME", "MECH"],
        "Civil": ["Civil", "CIVIL ENGG", "CE"],
        "Electronics": ["Electronics", "ELECTRONICS COMMUNICATION", "EC", "ECE"],
        "Electrical": ["Electrical", "ELECTRICAL ENGG", "EE"]
    }.get(department, [department])

    filters = []
    for token in department_tokens:
        filters.append(User.stream.ilike(f"%{token}%"))
        filters.append(User.class_name.ilike(f"%{token}%"))
        filters.append(User.subject_specialization.ilike(f"%{token}%"))
    return query.filter(or_(*filters))

def apply_section_filter(query, section):
    if section == "Section 1":
        return query.filter(or_(User.batch == "01", User.batch == "1", User.class_name.ilike("%1")))
    if section == "Section 2":
        return query.filter(or_(User.batch == "02", User.batch == "2", User.class_name.ilike("%2")))
    return query

def student_can_access_project(student_id, project_id):
    student = User.query.get(student_id)
    if not student:
        return False
    return ProjectCohortAssignment.query.filter_by(
        project_id=project_id,
        academic_year=student.academic_year,
        department=student.stream,
        class_name=student.class_name
    ).first() is not None

def cohort_student_query(project_id):
    assignment_rows = ProjectCohortAssignment.query.filter_by(project_id=project_id).all()
    query = User.query.filter_by(role='student', home_institution_code=session['institution_code'])
    if not assignment_rows:
        return query.filter(False)

    cohort_filters = []
    for row in assignment_rows:
        cohort_filters.append(and_(
            User.academic_year == row.academic_year,
            User.stream == row.department,
            User.class_name == row.class_name
        ))
    return query.filter(or_(*cohort_filters))

def assigned_student_query(project_id):
    team_student_ids = db.session.query(TeamAssignment.student_id).filter_by(project_id=project_id)
    if team_student_ids.count() > 0:
        return User.query.filter(
            User.role == 'student',
            User.home_institution_code == session['institution_code'],
            User.id.in_(team_student_ids)
        )
    return cohort_student_query(project_id)

def project_quiz_total(project_id, student_id):
    answers = StudentFlashcardAnswer.query.filter_by(project_id=project_id, student_id=student_id).all()
    return sum(a.marks_awarded or 0 for a in answers)

def project_quiz_complete(project_id, student_id):
    flashcard_count = ProjectFlashcard.query.filter_by(project_id=project_id).count()
    if flashcard_count == 0:
        return True
    answer_count = StudentFlashcardAnswer.query.filter_by(project_id=project_id, student_id=student_id).count()
    return answer_count >= flashcard_count

def team_generation_unlocked(project):
    try:
        deadline_dt = datetime.strptime(project.deadline, "%Y-%m-%d")
        if datetime.utcnow() >= deadline_dt:
            return True
    except ValueError:
        pass
    students = assigned_student_query(project.id).all()
    return bool(students) and all(project_quiz_complete(project.id, student.id) for student in students)

@app.route('/api/reports/discover-students', methods=['GET'])
def discover_students():
    if session.get('role') not in ['admin', 'faculty']: return jsonify({"error": "Unauthorized"}), 403
    query = User.query.filter_by(role='student', home_institution_code=session['institution_code'])
    
    query = apply_department_filter(query, request.args.get('department'))
    query = apply_section_filter(query, request.args.get('section'))
    if request.args.get('stream'): query = query.filter_by(stream=request.args.get('stream'))
    if request.args.get('class_name'): query = query.filter_by(class_name=request.args.get('class_name'))
    if request.args.get('batch'): query = query.filter_by(batch=request.args.get('batch'))
    if request.args.get('semester'): query = query.filter_by(semester=request.args.get('semester'))
    if request.args.get('academic_year'): query = query.filter_by(academic_year=request.args.get('academic_year'))
    
    students = query.all()
    return jsonify([{
        "name": s.real_name, "roll_no": s.student_roll_no, "class": s.class_name,
        "batch": s.batch, "semester": s.semester, "stream": s.stream, "year": s.academic_year,
        "age": s.age, "enrollment_year": s.enrollment_year
    } for s in students])

@app.route('/api/admin/pending-faculty', methods=['GET'])
def pending_faculty_directory():
    if session.get('role') != 'admin': return jsonify({"error": "Forbidden"}), 403
    faculty = User.query.filter_by(
        role='faculty',
        home_institution_code=session['institution_code'],
        is_approved=False
    ).order_by(User.real_name.asc()).all()
    return jsonify([{
        "id": f.id,
        "name": f.real_name,
        "faculty_id": f.faculty_id,
        "department": f.stream,
        "section": f.batch,
        "subject": f.subject_specialization,
        "year": f.academic_year
    } for f in faculty])

@app.route('/api/admin/approve-faculty/<int:user_id>', methods=['POST'])
def approve_faculty_access(user_id):
    if session.get('role') != 'admin': return jsonify({"error": "Forbidden"}), 403
    faculty = User.query.filter_by(
        id=user_id,
        role='faculty',
        home_institution_code=session['institution_code']
    ).first_or_404()
    faculty.is_approved = True
    db.session.commit()
    return jsonify({"success": True, "message": f"{faculty.real_name} can now access the faculty workspace."})

@app.route('/api/admin/create-user', methods=['POST'])
def admin_create_user():
    if session.get('role') != 'admin': return jsonify({"error": "Forbidden"}), 403
    data = request.json or {}
    role = data.get('role')
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    real_name = (data.get('real_name') or '').strip().upper()

    if role not in ['student', 'faculty']:
        return jsonify({"success": False, "message": "Choose student or faculty."})
    if not username or not password or not real_name:
        return jsonify({"success": False, "message": "Name, username, and password are required."})
    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username already exists."})

    student_roll_no = (data.get('student_roll_no') or '').strip().upper() if role == 'student' else None
    faculty_id = (data.get('faculty_id') or '').strip().upper() if role == 'faculty' else None

    if role == 'student':
        if not student_roll_no:
            return jsonify({"success": False, "message": "Student roll number is required."})
        if User.query.filter_by(student_roll_no=student_roll_no, role='student').first():
            return jsonify({"success": False, "message": "Student roll number already exists."})
    if role == 'faculty':
        if not faculty_id:
            return jsonify({"success": False, "message": "Faculty ID is required."})
        if User.query.filter_by(faculty_id=faculty_id, role='faculty').first():
            return jsonify({"success": False, "message": "Faculty ID already exists."})

    new_user = User(
        username=username,
        password_hash=secure_password(password),
        role=role,
        home_institution_code=session['institution_code'],
        real_name=real_name,
        stream=data.get('stream'),
        class_name=data.get('class_name'),
        batch=data.get('batch'),
        semester=data.get('semester'),
        academic_year=data.get('academic_year'),
        age=int(data.get('age')) if str(data.get('age') or '').strip() else None,
        enrollment_year=data.get('enrollment_year'),
        student_roll_no=student_roll_no,
        faculty_id=faculty_id,
        subject_specialization=data.get('subject_specialization') if role == 'faculty' else None,
        is_approved=True,
        account_claimed=True
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": f"{role.capitalize()} account created."})

@app.route('/api/admin/teacher-directory', methods=['GET'])
def teacher_directory():
    if session.get('role') != 'admin': return jsonify({"error": "Forbidden"}), 403
    query = User.query.filter_by(role='faculty', home_institution_code=session['institution_code'])
    query = apply_department_filter(query, request.args.get('department'))
    faculty = query.order_by(User.real_name.asc()).all()
    return jsonify([{
        "name": f.real_name,
        "faculty_id": f.faculty_id,
        "department": f.stream,
        "subject": f.subject_specialization,
        "status": "Approved" if f.is_approved else "Pending"
    } for f in faculty])

def project_completion_percentage(project):
    progress_rows = TeamProgress.query.filter_by(project_id=project.id).all()
    if progress_rows:
        return round(sum(row.completion_percentage for row in progress_rows) / len(progress_rows))

    assigned_students = assigned_student_query(project.id).with_entities(User.id).all()
    assigned_ids = [row.id for row in assigned_students]
    if not assigned_ids:
        return 0

    submitted_count = db.session.query(StudentCompetency.user_id).filter(
        StudentCompetency.project_id == project.id,
        StudentCompetency.user_id.in_(assigned_ids)
    ).distinct().count()
    return round((submitted_count / len(assigned_ids)) * 100)

@app.route('/api/faculty/project-completion-summary')
def faculty_project_completion_summary():
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    projects = Project.query.filter_by(institution_code=session['institution_code']).order_by(Project.created_at.desc()).all()
    payload = []
    for project in projects:
        assigned_count = assigned_student_query(project.id).count()
        team_count = db.session.query(TeamAssignment.team_number).filter_by(project_id=project.id).distinct().count()
        payload.append({
            "id": project.id,
            "name": project.project_name,
            "completion": project_completion_percentage(project),
            "assigned_students": assigned_count,
            "teams": team_count
        })
    return jsonify(payload)

@app.route('/api/faculty/project/<int:project_id>/team-completion')
def faculty_project_team_completion(project_id):
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    Project.query.filter_by(id=project_id, institution_code=session['institution_code']).first_or_404()

    team_numbers = {
        row.team_number for row in TeamAssignment.query.filter_by(project_id=project_id).all()
    }
    progress_rows = TeamProgress.query.filter_by(project_id=project_id).all()
    team_numbers.update(row.team_number for row in progress_rows)

    payload = []
    for team_number in sorted(team_numbers):
        progress = next((row for row in progress_rows if row.team_number == team_number), None)
        member_count = TeamAssignment.query.filter_by(project_id=project_id, team_number=team_number).count()
        payload.append({
            "team_number": team_number,
            "completion": progress.completion_percentage if progress else 0,
            "members": member_count,
            "summary": progress.status_summary if progress else "No progress update submitted yet."
        })
    return jsonify(payload)

@app.route('/api/project/deploy', methods=['POST'])
def api_deploy_project():
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    cohorts = data.get('cohorts') or []
    if not cohorts:
        return jsonify({"success": False, "message": "Select at least one academic year, department, and class."})

    cohort_label = "; ".join([f"{c.get('academic_year')} / {c.get('department')} / {c.get('class_name')}" for c in cohorts])
    new_p = Project(
        institution_code=session['institution_code'],
        project_name=data['name'],
        description=data['description'],
        deadline=data['deadline'],
        team_size=int(data['team_size']),
        class_batch=cohort_label[:50] if cohort_label else data.get('batch', 'Multi-cohort')
    )
    db.session.add(new_p)
    db.session.commit()

    for cohort in cohorts:
        academic_year = cohort.get('academic_year')
        department = cohort.get('department')
        class_name = cohort.get('class_name')
        if academic_year and department and class_name:
            db.session.add(ProjectCohortAssignment(
                project_id=new_p.id,
                academic_year=academic_year,
                department=department,
                class_name=class_name
            ))
    
    for s_name in data.get('skills', []):
        s_name_clean = s_name.strip()
        if not s_name_clean: continue
        skill_node = GlobalSkill.query.filter_by(skill_name=s_name_clean).first()
        if not skill_node:
            skill_node = GlobalSkill(skill_name=s_name_clean)
            db.session.add(skill_node)
            db.session.commit()
        db.session.add(ProjectSkillRequirement(project_id=new_p.id, skill_id=skill_node.id))

    for card in data.get('flashcards', []):
        question = (card.get('question') or '').strip()
        answer_guide = (card.get('answer_guide') or '').strip()
        if question and answer_guide:
            db.session.add(ProjectFlashcard(
                project_id=new_p.id,
                topic_tag=(card.get('topic_tag') or 'General').strip(),
                question=question,
                answer_guide=answer_guide,
                max_marks=max(1, int(card.get('max_marks') or 10))
            ))

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
    project = Project.query.get_or_404(pid)
    if project_completion_percentage(project) >= 30:
        return jsonify({
            "success": False,
            "message": "Skill self-assessment is locked because this project has reached 30% completion."
        }), 403
    
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

@app.route('/api/student/submit-flashcards', methods=['POST'])
def api_submit_flashcards():
    if session.get('role') != 'student': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    project_id = int(data.get('project_id'))
    if not student_can_access_project(session['user_id'], project_id):
        return jsonify({"success": False, "message": "This project is not assigned to your class."}), 403

    for flashcard_id, answer_text in (data.get('answers') or {}).items():
        flashcard = ProjectFlashcard.query.filter_by(id=int(flashcard_id), project_id=project_id).first()
        if not flashcard:
            continue
        answer = StudentFlashcardAnswer.query.filter_by(
            flashcard_id=flashcard.id,
            student_id=session['user_id']
        ).first()
        if answer:
            answer.answer_text = answer_text.strip()
        else:
            db.session.add(StudentFlashcardAnswer(
                project_id=project_id,
                flashcard_id=flashcard.id,
                student_id=session['user_id'],
                answer_text=answer_text.strip()
            ))
    db.session.commit()
    return jsonify({"success": True, "message": "Quiz answers saved."})

@app.route('/api/faculty/project/<int:project_id>/status-matrix')
def faculty_status_matrix(project_id):
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    Project.query.filter_by(id=project_id, institution_code=session['institution_code']).first_or_404()
    flashcards = ProjectFlashcard.query.filter_by(project_id=project_id).order_by(ProjectFlashcard.id.asc()).all()
    students = assigned_student_query(project_id).order_by(User.real_name.asc()).all()
    payload = []
    for student in students:
        answers = StudentFlashcardAnswer.query.filter_by(project_id=project_id, student_id=student.id).all()
        answer_lookup = {a.flashcard_id: a for a in answers}
        payload.append({
            "id": student.id,
            "name": student.real_name,
            "college_id": student.student_roll_no,
            "account_status": "Claimed" if student.account_claimed else "Unclaimed",
            "quiz_status": "Complete" if len(answers) >= len(flashcards) else "Pending",
            "marks": sum(a.marks_awarded or 0 for a in answers),
            "answers": [{
                "flashcard_id": card.id,
                "topic": card.topic_tag,
                "question": card.question,
                "answer": answer_lookup[card.id].answer_text if card.id in answer_lookup else "",
                "marks_awarded": answer_lookup[card.id].marks_awarded if card.id in answer_lookup else None,
                "max_marks": card.max_marks
            } for card in flashcards]
        })
    return jsonify(payload)

@app.route('/api/faculty/project/<int:project_id>/grade-answer', methods=['POST'])
def grade_flashcard_answer(project_id):
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    answer = StudentFlashcardAnswer.query.filter_by(
        project_id=project_id,
        student_id=int(data.get('student_id')),
        flashcard_id=int(data.get('flashcard_id'))
    ).first_or_404()
    card = ProjectFlashcard.query.get_or_404(answer.flashcard_id)
    answer.marks_awarded = max(0, min(card.max_marks, int(data.get('marks') or 0)))
    db.session.commit()
    return jsonify({"success": True, "message": "Marks saved."})

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
    outstanding_students = assigned_student_query(project_id).filter(~User.id.in_(participated_subquery)).all()
    return jsonify([{"id": s.id, "name": s.real_name, "roll_no": s.student_roll_no, "class": s.class_name, "batch": s.batch} for s in outstanding_students])

@app.route('/api/project/<int:project_id>/generate-teams', methods=['POST'])
def generate_teams(project_id):
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    project = Project.query.get_or_404(project_id)
    if not team_generation_unlocked(project):
        return jsonify({"success": False, "message": "Team generation unlocks after the deadline passes or every assigned student completes the quiz."})
    target_size = project.team_size
    
    competent_roster = db.session.query(User.id, db.func.sum(StudentCompetency.score).label('total_weight')).join(
        StudentCompetency, User.id == StudentCompetency.user_id
    ).filter(
        StudentCompetency.project_id == project_id,
        User.id.in_(assigned_student_query(project_id).with_entities(User.id))
    ).group_by(User.id).all()
    weighted_roster = []
    for student_id, skill_weight in competent_roster:
        weighted_roster.append({
            "id": student_id,
            "weight": int(skill_weight or 0) + project_quiz_total(project_id, student_id)
        })
    weighted_roster.sort(key=lambda row: row["weight"], reverse=True)
    
    if not weighted_roster:
        return jsonify({"success": False, "message": "Matchmaking halted: No student metrics recorded yet."})
        
    TeamAssignment.query.filter_by(project_id=project_id).delete()
    total_count = len(weighted_roster)
    num_teams = max(1, total_count // target_size)
    teams_accumulator = [[] for _ in range(num_teams)]
    
    for rank_idx, student in enumerate(weighted_roster):
        wave_cycle = rank_idx // num_teams
        target_bucket = rank_idx % num_teams
        if wave_cycle % 2 != 0:
            target_bucket = (num_teams - 1) - target_bucket
        teams_accumulator[target_bucket].append(student["id"])
        
    for team_idx, members in enumerate(teams_accumulator):
        t_num = team_idx + 1
        for m_id in members:
            db.session.add(TeamAssignment(project_id=project_id, student_id=m_id, team_number=t_num))
            
    db.session.commit()
    return jsonify({"success": True, "message": f"Optimization engine complete! Formed {num_teams} balanced clusters."})

@app.route('/api/project/<int:project_id>/roster-report')
def get_roster_report(project_id):
    records = db.session.query(TeamAssignment.team_number, User.id, User.real_name, User.username, User.student_roll_no, TeamAssignment.is_team_lead).join(
        User, TeamAssignment.student_id == User.id
    ).filter(TeamAssignment.project_id == project_id).order_by(TeamAssignment.team_number.asc()).all()
    
    report_dictionary = {}
    for t_num, student_id, r_name, u_name, roll_no, is_lead in records:
        if t_num not in report_dictionary: report_dictionary[t_num] = []
        report_dictionary[t_num].append({"id": student_id, "name": r_name, "username": u_name, "roll_no": roll_no, "is_lead": is_lead})
    return jsonify(report_dictionary)

@app.route('/api/project/<int:project_id>/eligible-students')
def eligible_students(project_id):
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    assigned_ids = db.session.query(TeamAssignment.student_id).filter_by(project_id=project_id).subquery()
    students = cohort_student_query(project_id).filter(~User.id.in_(assigned_ids)).order_by(User.real_name.asc()).all()
    return jsonify([{"id": s.id, "name": s.real_name, "college_id": s.student_roll_no, "class": s.class_name} for s in students])

@app.route('/api/faculty/project/<int:project_id>/team-edit', methods=['POST'])
def edit_team(project_id):
    if session.get('role') != 'faculty': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    action = data.get('action')
    student_id = int(data.get('student_id'))

    if action == 'remove':
        TeamAssignment.query.filter_by(project_id=project_id, student_id=student_id).delete()
    elif action in ['move', 'add']:
        team_number = int(data.get('team_number'))
        row = TeamAssignment.query.filter_by(project_id=project_id, student_id=student_id).first()
        if row:
            row.team_number = team_number
        elif student_can_access_project(student_id, project_id):
            db.session.add(TeamAssignment(project_id=project_id, student_id=student_id, team_number=team_number))
        else:
            return jsonify({"success": False, "message": "Student is outside this project's assigned cohorts."})
    elif action == 'leader':
        team_number = int(data.get('team_number'))
        TeamAssignment.query.filter_by(project_id=project_id, team_number=team_number).update({"is_team_lead": False})
        row = TeamAssignment.query.filter_by(project_id=project_id, student_id=student_id, team_number=team_number).first()
        if row:
            row.is_team_lead = True
    else:
        return jsonify({"success": False, "message": "Unsupported team edit."})

    db.session.commit()
    return jsonify({"success": True, "message": "Team updated."})

@app.route('/api/project/<int:project_id>/messages')
def project_messages(project_id):
    if session.get('role') not in ['faculty', 'student']: return jsonify({"error": "Forbidden"}), 403
    channel_type = request.args.get('channel_type', 'private')
    query = CommunicationMessage.query.filter_by(project_id=project_id, channel_type=channel_type)
    if session.get('role') == 'student':
        if not student_can_access_project(session['user_id'], project_id):
            return jsonify({"error": "Forbidden"}), 403
        if channel_type == 'private':
            query = query.filter(or_(CommunicationMessage.sender_id == session['user_id'], CommunicationMessage.recipient_id == session['user_id']))
        else:
            assignment = TeamAssignment.query.filter_by(project_id=project_id, student_id=session['user_id']).first()
            if not assignment or not assignment.is_team_lead:
                return jsonify({"error": "Only the team lead can access the faculty doubt chat."}), 403
            query = query.filter_by(team_number=assignment.team_number if assignment else 0)
    elif request.args.get('team_number'):
        query = query.filter_by(team_number=int(request.args.get('team_number')))

    messages = query.order_by(CommunicationMessage.created_at.asc()).all()
    sender_ids = {m.sender_id for m in messages}
    users = {u.id: u for u in User.query.filter(User.id.in_(sender_ids)).all()} if sender_ids else {}
    return jsonify([{
        "id": m.id,
        "sender": users[m.sender_id].real_name if m.sender_id in users else "Unknown",
        "sender_role": users[m.sender_id].role if m.sender_id in users else "",
        "body": m.body,
        "channel_type": m.channel_type,
        "team_number": m.team_number,
        "created_at": m.created_at.strftime("%Y-%m-%d %H:%M")
    } for m in messages])

@app.route('/api/project/<int:project_id>/messages', methods=['POST'])
def send_project_message(project_id):
    if session.get('role') not in ['faculty', 'student']: return jsonify({"error": "Forbidden"}), 403
    data = request.json
    channel_type = data.get('channel_type', 'private')
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({"success": False, "message": "Message cannot be empty."})

    recipient_id = data.get('recipient_id')
    team_number = data.get('team_number')
    if session.get('role') == 'student':
        if not student_can_access_project(session['user_id'], project_id):
            return jsonify({"error": "Forbidden"}), 403
        if channel_type == 'team':
            assignment = TeamAssignment.query.filter_by(project_id=project_id, student_id=session['user_id']).first()
            if not assignment or not assignment.is_team_lead:
                return jsonify({"success": False, "message": "Only the team lead can ask doubts to faculty."}), 403
            team_number = assignment.team_number if assignment else None
            recipient_id = None
        else:
            recipient_id = None
    elif channel_type == 'team' and not team_number:
        return jsonify({"success": False, "message": "Select a team before sending a reply."})

    db.session.add(CommunicationMessage(
        project_id=project_id,
        sender_id=session['user_id'],
        recipient_id=int(recipient_id) if recipient_id else None,
        team_number=int(team_number) if team_number else None,
        channel_type=channel_type,
        body=body
    ))
    db.session.commit()
    return jsonify({"success": True, "message": "Message sent."})

@app.route('/api/project/<int:project_id>/messages', methods=['DELETE'])
def clear_project_messages(project_id):
    if session.get('role') not in ['faculty', 'student']: return jsonify({"error": "Forbidden"}), 403
    channel_type = request.args.get('channel_type', 'team')
    query = CommunicationMessage.query.filter_by(project_id=project_id, channel_type=channel_type)

    if session.get('role') == 'student':
        if not student_can_access_project(session['user_id'], project_id):
            return jsonify({"error": "Forbidden"}), 403
        assignment = TeamAssignment.query.filter_by(project_id=project_id, student_id=session['user_id']).first()
        if channel_type != 'team' or not assignment or not assignment.is_team_lead:
            return jsonify({"success": False, "message": "Only the team lead can clear this team chat."}), 403
        query = query.filter_by(team_number=assignment.team_number)
    elif request.args.get('team_number'):
        query = query.filter_by(team_number=int(request.args.get('team_number')))

    deleted_count = query.delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"success": True, "message": f"Deleted {deleted_count} chat message(s)."})


# ==========================================
# INSTITUTION COHORT ONBOARDING GATEWAYS
# ==========================================

@app.route('/register-institution')
def register_institution_page():
    return redirect(url_for('role_selection'))

@app.route('/api/institution/register', methods=['POST'])
def api_register_institution():
    return jsonify({"success": False, "message": "Institution onboarding is disabled for this MBCET-only workspace."}), 403

if __name__ == '__main__':
    app.run(debug=True)
