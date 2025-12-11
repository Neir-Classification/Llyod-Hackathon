# Setup and Run Guide

This guide provides step-by-step instructions to set up and run the Lyyod Hackathon project.

## Prerequisites

- Python 3.10 or higher
- Node.js 18.x or higher
- npm 9.x or higher
- Git

## Project Structure

This is a full-stack application with:
- **Backend**: FastAPI (Python) - AI-powered insurance chatbot with RAG
- **Frontend**: React + TypeScript + Vite

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Lyyod-Hackathon
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Node.js Dependencies

```bash
npm install
```

---

## Configuration

### 1. Environment Variables

Create a `.env` file in the root directory:

```bash
cp env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 2. Database Setup

Initialize the database with seed data:

```bash
python seed_database.py
```

This will create:
- SQLite database (`insurance.db`)
- Sample users with policies
- Test data for tickets and call summaries

### 3. Build FAISS Index (Optional)

If you need to rebuild the vector store from PDF documents:

```bash
python rebuild_embeddings.py
```

Or with Gemini embeddings:

```bash
python rebuild_with_gemini.py
```

---

## Running the Application

### Method 1: Run Both Backend and Frontend Separately

#### Terminal 1 - Backend Server

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Run FastAPI backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be available at: `http://localhost:8000`

#### Terminal 2 - Frontend Development Server

```bash
# Run React frontend
npm run dev
```

The frontend will be available at: `http://localhost:5173`

### Method 2: Run Backend Only

If you only need the API server:

```bash
source .venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Documentation

Once the backend is running, you can access:

- **Interactive API Docs (Swagger)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

---

## Testing

### Test Authentication

```bash
python test_auth.py
```

### Test JWT Token Generation

```bash
python test_jwt.py
```

### Test Ticket Creation

```bash
python test_ticket_creation.py
```

### Test PDF Extraction

```bash
python test_pdf_extraction.py
```

---

## Development Commands

### Backend Development

```bash
# Activate virtual environment
source .venv/bin/activate

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Check database users
python debug_users.py

# View FAISS index statistics
python view_faiss_stats.py

# Check embeddings
python check_embeddings.py
```

### Frontend Development

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Common Issues and Solutions

### Issue: Port Already in Use

**Backend (Port 8000):**
```bash
# Check what's using port 8000
lsof -ti:8000

# Kill the process
kill $(lsof -ti:8000)
```

**Frontend (Port 5173):**
```bash
# Check what's using port 5173
lsof -ti:5173

# Kill the process
kill $(lsof -ti:5173)
```

### Issue: Module Not Found

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Database Not Found

```bash
# Recreate database with seed data
python seed_database.py
```

### Issue: FAISS Index Not Found

```bash
# Rebuild FAISS index
python rebuild_embeddings.py
```

---

## Project Components

### Backend Files
- `main.py` - Main FastAPI application with all endpoints
- `database.py` - SQLAlchemy models and database configuration
- `ai_safety.py` - AI safety and content moderation
- `explainability.py` - Response explainability and citations
- `seed_database.py` - Database initialization script

### Frontend Files
- `src/App.tsx` - Main React application
- `src/components/` - React components
- `src/hooks/` - Custom React hooks
- `vite.config.ts` - Vite configuration
- `tailwind.config.js` - Tailwind CSS configuration

### Utility Scripts
- `rebuild_embeddings.py` - Rebuild FAISS vector store
- `check_embeddings.py` - Verify embeddings quality
- `debug_users.py` - Debug user database
- `test_*.py` - Various test scripts

---

## API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - User login
- `GET /api/me` - Get current user info

### Chat & RAG
- `POST /api/transcribe` - Transcribe audio to text
- `POST /api/query-rag` - Query the RAG system
- `POST /api/text-to-speech` - Convert text to speech
- `POST /api/transcribe-and-query` - Combined transcribe + query

### Tickets
- `POST /api/tickets` - Create support ticket
- `GET /api/tickets` - Get user's tickets
- `GET /api/tickets/{ticket_id}` - Get specific ticket

### Policies
- `GET /api/policies` - Get user's policies
- `GET /api/policies/{policy_id}` - Get specific policy

### Admin
- `GET /api/admin/tickets` - Get all tickets (admin only)
- `PUT /api/admin/tickets/{ticket_id}` - Update ticket (admin only)

---

## Default Test Credentials

After running `seed_database.py`, you can use these test accounts:

**Regular User:**
- Email: `john.doe@example.com`
- Password: `password123`

**Admin User:**
- Email: `admin@insurance.com`
- Password: `admin123`

---

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT and embeddings | Yes |
| `SECRET_KEY` | JWT secret key (auto-generated if not set) | No |
| `ALGORITHM` | JWT algorithm (default: HS256) | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time (default: 30) | No |

---

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **OpenAI API** - GPT-4 for chat and Whisper for transcription
- **LangChain** - RAG pipeline and document processing
- **FAISS** - Vector similarity search
- **SQLAlchemy** - Database ORM
- **Python-JOSE** - JWT authentication
- **Bcrypt** - Password hashing

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **OGL** - WebGL library for 3D effects

---

## Production Deployment

### Build Frontend

```bash
npm run build
```

This creates a `dist/` directory with production-ready files.

### Run Backend in Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review the code in `main.py` for endpoint details
3. Check terminal logs for error messages
4. Ensure all environment variables are set correctly

---

## License

[Add your license information here]
