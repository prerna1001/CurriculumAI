# Backend setup

Use Python 3.9 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Copy `.env.example` to `.env` and set local service credentials before running the live research or agent workflow. Do not commit `.env`.

The backend creates SQLite data at `./data/curriculumai.db` by default. Check the foundation with `http://localhost:8000/health`.
