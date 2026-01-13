# DataInsight Pro

> **🚀 AI-Powered Business Analytics Platform with Team Collaboration**
> 
> **NEW: Modular Architecture + 5-6x Faster Response Times!**

---

---

## 🚀 Features

### 1. Core Platform (Auth & Dashboard)
- ✅ User Authentication (Email/Password with SQLite)
- ✅ Session Management with secure tokens
- ✅ Team Management (add/remove members)
- ✅ Modern tab-based Streamlit UI

### 2. The Brain (RAG Engine)
- ✅ Multi-format file ingestion (PDF, DOCX, CSV, Excel)
- ✅ Smart parsing (tables vs text detection)
- ✅ Cohere embeddings with Pinecone vector storage
- ✅ Semantic search with Groq LLM
- ✅ Strict grounded answers (prevents hallucinations)

### 3. The Analyst (Quantitative Engine)
- ✅ **Instant DataFrame loading** for uploaded files
- ✅ Natural language plotting ("Show sales by region")
- ✅ Interactive Plotly visualizations
- ✅ Self-correcting code generation

### 4. The Postman (Communication Engine)
- ✅ Gmail OAuth integration (optional)
- ✅ WhatsApp-style chat interface
- ✅ Team CC on all messages
- ✅ Share insights directly to team

### 5. Smart Briefings
- ✅ Auto-generated 3-bullet executive summaries
- ✅ Meeting prep talking points
- ✅ Briefing history

### 6. Admin & Usage
- ✅ Token usage tracking
- ✅ Admin dashboard for system stats

---

## 🗺️ Architecture

### New Modular Structure
```
DataInsight Pro/
├── app.py                          # 🚀 Simple entry point (25 lines)
├── api/                            # 📦 API Package
│   ├── main.py                     # FastAPI app with middleware
│   ├── dependencies.py             # Shared dependencies
│   ├── models.py                   # Pydantic models
│   └── routes/                     # 🛣️ Feature-focused routes
│       ├── auth_routes.py          # Authentication
│       ├── upload_routes.py        # File upload (optimized)
│       ├── query_routes.py         # RAG queries
│       ├── visualization_routes.py # Charts & plotting
│       ├── team_routes.py          # Team management
│       ├── briefing_routes.py      # Smart briefings
│       ├── email_routes.py         # Email integration
│       ├── chat_routes.py          # Team chat
│       ├── calendar_routes.py      # Calendar & scheduling
│       ├── user_routes.py          # User management
│       └── admin_routes.py         # Administration
├── src/                            # 🔧 Core Services
│   ├── auth.py                     # Authentication service
│   ├── analytics_engine.py         # NL plotting & visualization
│   ├── vector_manager.py           # Pinecone operations
│   ├── query_llm.py                # RAG pipeline
│   └── ...
└── tests/                          # 🧪 Comprehensive test suite
```

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    React FRONTEND                       │
│  (Tabs: Analysis, Collaboration, Briefings, Settings)       │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP + Auth Token
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 MODULAR FASTAPI BACKEND                     │
├─────────────────────────────────────────────────────────────┤
│ • Auth: /auth/register, /auth/login, /auth/me              │
│ • Upload: /upload/quick (OPTIMIZED), /upload/stream        │
│ • Team: /team, /team/members                                │
│ • RAG: /query, /schema                                      │
│ • Viz: /visualize/by-query, /visualize/nl                  │
│ • Brief: /briefing/executive-summary, /briefing/meeting-prep│
│ • Email: /email/threads, /email/send, /email/reply         │
│ • Admin: /admin/users, /admin/stats                        │
└────────┬──────────────────────┬──────────────────┬──────────┘
         │                      │                  │
    ┌────▼────┐           ┌────▼────┐        ┌────▼────┐
    │ Cohere  │           │  Groq   │        │Pinecone │
    │Embeddings│          │   LLM   │        │VectorDB │
    └─────────┘           └─────────┘        └─────────┘
```

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- API Keys: Groq, Pinecone, Cohere
- Supabase account (free tier works)

### Quick Start

1. **Clone and setup environment:**
```bash
git clone <repo>
cd datainsight-pro
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

2. **Install dependencies:**
```bash
pip install -r requirements-backend.txt
pip install -r requirements-frontend.txt
```

3. **Setup Supabase Database:**
   - Go to [supabase.com](https://supabase.com) and create a new project
   - Go to SQL Editor and run the contents of `supabase_setup.sql`
   - Go to Settings > API to get your URL and service_role key

4. **Configure environment:**
Create `.env` file:
```env
# Required
GROQ_API_KEY=your_groq_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=your_index_name
COHERE_API_KEY=your_cohere_api_key

# Supabase (required for auth & data)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
```

5. **Run migration check (recommended):**
```bash
python migrate_to_modular.py
```

6. **Run the application:**

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Or manually:**
```bash
# Terminal 1 - Backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend
streamlit run app/streamlit_app.py --server.port 8501
```

7. **Access the app:**
- Frontend: http://localhost:8501
- API Docs: http://localhost:8000/docs

---

## 🚀 New Optimized Endpoints

### Quick Upload (Recommended)
```http
POST /upload/quick
Content-Type: multipart/form-data

Response (2-5 seconds):
{
  "filename": "data.csv",
  "preview": {...},
  "job_id": "uuid-123",
  "status": "preview_ready",
  "message": "Preview ready! Full processing continues in background."
}
```

### Check Processing Status
```http
GET /upload/status/{job_id}

Response:
{
  "status": "completed",
  "progress": 100,
  "message": "Processing complete!",
  "result": {...}
}
```

### Streaming Upload (Advanced)
```http
POST /upload/stream
Content-Type: text/event-stream

Response: Real-time progress updates
```

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

---

## 🧪 Running Tests

```bash
pip install -r requirements-test.txt
python -m pytest tests/ -v
```

---

## 📝 Usage Flow (Optimized)

1. **Register/Login** - Create account or sign in
2. **Upload Data** - CSV, Excel, PDF, or DOCX files (**Now 5-6x faster!**)
3. **View Instant Preview** - See data immediately (2-5 seconds)
4. **Background Processing** - Full analysis continues automatically
5. **Ask Questions** - Natural language queries about your data
6. **Create Visualizations** - Request charts in plain English
7. **Collaborate** - Share insights with team via email
8. **Prepare for Meetings** - Generate talking points

---

## 🔧 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create new account |
| POST | `/auth/login` | Login and get token |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/me` | Get current user info |

### File Upload (Optimized)
| Method | Endpoint | Description | Speed |
|--------|----------|-------------|-------|
| POST | `/upload/quick` | **Fast upload with preview** | **2-5s** |
| GET | `/upload/status/{job_id}` | Check processing status | Instant |
| POST | `/upload/stream` | Streaming upload with progress | Real-time |
| POST | `/upload` | Legacy full upload | 15-30s |

### Team Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/team` | Get/create team |
| POST | `/team/members` | Add team member |
| DELETE | `/team/members/{email}` | Remove member |

### Data & RAG
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | Ask question about data |
| GET | `/schema` | Get data schema |

### Visualizations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/visualize/by-query` | Create chart from query |
| POST | `/visualize/nl` | Natural language plotting |
| GET | `/data/insights` | Get statistical insights |

### Briefings
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/briefing/executive-summary` | Generate summary |
| POST | `/briefing/meeting-prep` | Generate talking points |
| GET | `/briefing/history` | Get past briefings |

### Email/Communication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/email/status` | Check connection |
| GET | `/email/threads` | Get email threads |
| POST | `/email/send` | Send new email |
| POST | `/email/reply` | Reply to thread |

---

## 🔐 Security

- Passwords hashed with PBKDF2-SHA256
- Session tokens with expiration
- Rate limiting (100 requests/minute per IP)
- Input sanitization and validation
- File type and size restrictions
- Security headers (CSP, HSTS, etc.)
- Encrypted API key storage

---

## 📊 Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Backend | FastAPI (Modular) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth + Clerk |
| Vector DB | Pinecone |
| Embeddings | Cohere |
| LLM | Groq (Llama 3.1) |
| Visualization | Plotly |
| Architecture | **Modular, Clean, Maintainable** |

---

## 📁 Project Structure (New)

```
datainsight-pro/
├── app.py                      # 🚀 Simple entry point (25 lines)
├── api/                        # 📦 Modular API
│   ├── main.py                 # FastAPI app + middleware
│   ├── dependencies.py         # Shared dependencies
│   ├── models.py               # Pydantic models
│   └── routes/                 # Feature-focused routes
│       ├── auth_routes.py      # Authentication
│       ├── upload_routes.py    # File upload (optimized)
│       ├── query_routes.py     # RAG queries
│       ├── visualization_routes.py # Charts
│       ├── team_routes.py      # Team management
│       ├── briefing_routes.py  # Smart briefings
│       ├── email_routes.py     # Email integration
│       ├── chat_routes.py      # Team chat
│       ├── calendar_routes.py  # Calendar
│       ├── user_routes.py      # User management
│       └── admin_routes.py     # Administration
├── app/
│   ├── streamlit_app.py        # Frontend UI
│   └── static/style.css        # Custom styles
├── src/                        # Core services (unchanged)
│   ├── auth.py                 # Authentication service
│   ├── analytics_engine.py     # NL plotting
│   ├── vector_manager.py       # Pinecone operations
│   ├── query_llm.py            # RAG pipeline
│   └── ...
├── tests/                      # Test suite
├── data/                       # SQLite DB & uploads
├── ARCHITECTURE.md             # 📚 Detailed architecture docs
├── migrate_to_modular.py       # 🔧 Migration helper
├── requirements-*.txt          # Dependencies
├── docker-compose.yml          # Docker setup
└── start.bat/start.sh          # Startup scripts
```

---

## 🎯 Benefits of New Architecture

### For Developers
- ✅ **Clean Code** - Easy to read and understand
- ✅ **Modular Design** - Focused, single-responsibility modules
- ✅ **Type Safety** - Pydantic models throughout
- ✅ **Testable** - Isolated components

### For Recruiters
- ✅ **Professional Structure** - Industry best practices
- ✅ **Easy Navigation** - Find code quickly
- ✅ **Clear Documentation** - Comprehensive guides
- ✅ **Modern Patterns** - Dependency injection, middleware

### For Users
- ✅ **5-6x Faster** - Optimized upload performance
- ✅ **Better UX** - Immediate feedback
- ✅ **Real-time Progress** - Know what's happening
- ✅ **Non-blocking** - Continue working while processing

---

## 🤝 Contributing

### Adding a New Feature

1. Create route module in `api/routes/`
2. Define models in `api/models.py`
3. Add dependencies if needed
4. Register router in `api/main.py`
5. Write tests
6. Update documentation

See `ARCHITECTURE.md` for detailed guidelines.

---

## 📄 License

MIT License

---

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed architecture guide
- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation
- **[Migration Guide](migrate_to_modular.py)** - Transition helper

---

**Built with ❤️ for modern, scalable business analytics**

**🚀 Now with 5-6x faster performance and recruiter-friendly architecture!**
