from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ==========================================
# CENTRAL TENANCY & INSTITUTION LEDGERS
# ==========================================

class Institution(db.Model):
    __tablename__ = 'institutions'
    id = db.Column(db.Integer, primary_key=True)
    institution_code = db.Column(db.String(30), unique=True, nullable=False) # Unique short code index
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.Text, nullable=False)
    
    # Structural Constraint Format Strings (Descriptive layout templates, e.g., "B24CS1201")
    roll_no_format = db.Column(db.String(100), default="B24CS1201")
    faculty_id_format = db.Column(db.String(100), default="FAC-CS-XXXX")
    batch_format = db.Column(db.String(100), default="Batch XX")
    class_format = db.Column(db.String(100), default="CSX / ECX")
    academic_year_format = db.Column(db.String(100), default="202X-202X")
    semester_format = db.Column(db.String(100), default="S1 to S8")
    subject_format = db.Column(db.String(100), default="CSXXX")
    stream_format = db.Column(db.String(100), default="B.Tech / M.Tech")

class CrossTenantAccessRequest(db.Model):
    __tablename__ = 'cross_tenant_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    source_institution_code = db.Column(db.String(30), nullable=False)
    target_institution_code = db.Column(db.String(30), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="PENDING") # PENDING, APPROVED, REJECTED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================
# MASTER PROFILES (Isorole Matrix Mappings)
# ==========================================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'faculty', 'student'
    home_institution_code = db.Column(db.String(30), db.ForeignKey('institutions.institution_code', ondelete='CASCADE'), nullable=False)
    
    # Profile Matrix Metadata Attributes
    real_name = db.Column(db.String(100), nullable=False)
    stream = db.Column(db.String(100), nullable=True)
    subject_specialization = db.Column(db.String(100), nullable=True)
    class_name = db.Column(db.String(50), nullable=True)
    batch = db.Column(db.String(50), nullable=True)
    semester = db.Column(db.String(20), nullable=True)
    academic_year = db.Column(db.String(30), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    enrollment_year = db.Column(db.String(10), nullable=True)
    
    faculty_id = db.Column(db.String(50), nullable=True)
    student_roll_no = db.Column(db.String(50), nullable=True)
    is_approved = db.Column(db.Boolean, default=True, nullable=False)
    account_claimed = db.Column(db.Boolean, default=True, nullable=False)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    institution_code = db.Column(db.String(30), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.String(50), nullable=False)
    team_size = db.Column(db.Integer, nullable=False)
    class_batch = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProjectCohortAssignment(db.Model):
    __tablename__ = 'project_cohort_assignments'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    academic_year = db.Column(db.String(30), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)

    __table_args__ = (db.UniqueConstraint('project_id', 'academic_year', 'department', 'class_name', name='_project_cohort_uc'),)

class ProjectFlashcard(db.Model):
    __tablename__ = 'project_flashcards'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    topic_tag = db.Column(db.String(80), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer_guide = db.Column(db.Text, nullable=False)
    max_marks = db.Column(db.Integer, nullable=False, default=10)

class StudentFlashcardAnswer(db.Model):
    __tablename__ = 'student_flashcard_answers'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    flashcard_id = db.Column(db.Integer, db.ForeignKey('project_flashcards.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    marks_awarded = db.Column(db.Integer, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('flashcard_id', 'student_id', name='_flashcard_answer_uc'),)

class GlobalSkill(db.Model):
    __tablename__ = 'global_skills'
    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(50), unique=True, nullable=False)

# ==========================================
# COLLABORATION & MILESTONE TRACKING TABLES
# ==========================================

class ProjectSkillRequirement(db.Model):
    __tablename__ = 'project_skill_requirements'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('global_skills.id', ondelete='CASCADE'), nullable=False)

class StudentCompetency(db.Model):
    __tablename__ = 'student_competencies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('global_skills.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Integer, nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'project_id', 'skill_id', name='_student_tenant_uc'),)

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    availability_matrix = db.Column(db.String(100), nullable=False)

class TeamAssignment(db.Model):
    __tablename__ = 'team_assignments'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    team_number = db.Column(db.Integer, nullable=False)
    is_team_lead = db.Column(db.Boolean, default=False) # Core Requirement: Identifies Team Lead role

class TeamProgress(db.Model):
    __tablename__ = 'team_progress_logs'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    team_number = db.Column(db.Integer, nullable=False)
    completion_percentage = db.Column(db.Integer, default=0) # Scale metrics: 0 to 100
    status_summary = db.Column(db.Text, default="Team initialization pass complete.")
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DoubtTicket(db.Model):
    __tablename__ = 'doubt_resolution_tickets'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    team_number = db.Column(db.Integer, nullable=False)
    raised_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    query_text = db.Column(db.Text, nullable=False)
    faculty_response = db.Column(db.Text, nullable=True)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommunicationMessage(db.Model):
    __tablename__ = 'communication_messages'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    team_number = db.Column(db.Integer, nullable=True)
    channel_type = db.Column(db.String(20), nullable=False, default='private')
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

