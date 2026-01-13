#!/bin/bash
echo "========================================"
echo "  DataInsight Pro - Startup Script"
echo "========================================"
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create a .env file with your API keys:"
    echo "  GROQ_API_KEY=your_groq_key"
    echo "  PINECONE_API_KEY=your_pinecone_key"
    echo "  PINECONE_INDEX=your_index_name"
    echo "  COHERE_API_KEY=your_cohere_key"
    exit 1
fi

# Create data directory if not exists
mkdir -p data

# Install dependencies
echo "Checking dependencies..."
pip install -r requirements-backend.txt -q
pip install -r requirements-frontend.txt -q

echo
echo "Starting Backend Server..."
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

echo "Starting Frontend Server..."
streamlit run app/streamlit_app.py --server.port 8501 &
FRONTEND_PID=$!

echo
echo "========================================"
echo "  DataInsight Pro is running!"
echo "========================================"
echo
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:8501"
echo
echo "  API Docs: http://localhost:8000/docs"
echo
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
