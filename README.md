# SyncTeam

SyncTeam is a web-based platform designed to simplify and improve the process of forming academic project teams. The system aims to help faculty members create balanced student teams by considering factors such as technical skills, soft skills, project interests, and availability schedules.

Traditional team formation methods often result in unbalanced teams, scheduling conflicts, and unequal participation. SyncTeam addresses these challenges by providing a centralized platform where students can submit their project preferences and faculty members can manage project campaigns efficiently.

The long-term goal of the project is to implement an intelligent team formation engine that automatically generates balanced teams based on student competencies, project requirements, and schedule compatibility.


## Pages

- Role Selection Page
- Login Page
- Signup Page
- Student Dashboard
- Student Project View Page
- Faculty Dashboard
- Create Project Page
- Admin Dashboard

## Project Structure

```text
SYNCTEAM
│
├── app.py
├── db.py
├── syncteam.db
│
├── static
│   ├── css
│   │   └── dashboard.css
│   │
│   └── js
│       ├── auth.js
│       ├── faculty.js
│       └── student.js
│
└── templates
    ├── base.html
    ├── login.html
    ├── signup.html
    ├── role_selection.html
    ├── faculty_dashboard.html
    ├── faculty_create_project.html
    ├── student_dashboard.html
    ├── student_project_view.html
    └── admin_dashboard.html
```
