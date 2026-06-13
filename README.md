# SyncTeam

SyncTeam is a role-balanced and schedule-synchronized web portal for academic team formation.

## Run

```powershell
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5050`.

## Pages

- Role selection
- Faculty login/signup
- Student login/signup
- Admin login/signup
- Faculty dashboard
- New project publishing form
- Generated teams print view
- Faculty analytics
- Student dashboard
- Student project skill and schedule submission
- Student team hub
- Admin dashboard
- Admin user management

## Project Structure

```text
SyncTeam/
├── instance/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   ├── admin/
│   ├── faculty/
│   ├── public/
│   └── student/
├── app.py
├── requirements.txt
└── README.md
```
