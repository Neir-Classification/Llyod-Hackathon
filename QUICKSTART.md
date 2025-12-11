# Quick Start Guide

## TL;DR - Get Running in 5 Minutes

### 1. Setup Python Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### 2. Setup Node.js Dependencies
```bash
npm install
```

### 3. Configure Environment
```bash
cp env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 4. Initialize Database
```bash
python seed_database.py
```

### 5. Run Backend (Terminal 1)
```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Run Frontend (Terminal 2)
```bash
npm run dev
```

### 7. Access the Application
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Test Credentials

**User Login:**
- Email: `john.doe@example.com`
- Password: `password123`

**Admin Login:**
- Email: `admin@insurance.com`
- Password: `admin123`

---

## Common Commands

### Kill Processes on Ports
```bash
# Kill backend (port 8000)
kill $(lsof -ti:8000)

# Kill frontend (port 5173)
kill $(lsof -ti:5173)
```

### Rebuild Database
```bash
python seed_database.py
```

### Rebuild FAISS Index
```bash
python rebuild_embeddings.py
```

---

For detailed instructions, see [SETUP.md](SETUP.md)
