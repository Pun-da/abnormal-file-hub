#!/bin/bash
# Essential RAG System Starter
# Starts: Redis, Django, Celery Worker, and React Frontend

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting RAG Semantic Search System${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Redis
echo -e "${BLUE}[1/4] Checking Redis...${NC}"
if redis-cli ping >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${YELLOW}Starting Redis...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start redis >/dev/null 2>&1 || redis-server --daemonize yes
    else
        sudo systemctl start redis 2>/dev/null || redis-server --daemonize yes
    fi
    sleep 2
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis started${NC}"
    else
        echo -e "${RED}✗ Failed to start Redis${NC}"
        exit 1
    fi
fi

# Start Django
echo ""
echo -e "${BLUE}[2/4] Starting Django Backend...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi
source venv/bin/activate
cd ..

mkdir -p logs
kill $(lsof -ti:8000) 2>/dev/null || true
cd backend
nohup python manage.py runserver 0.0.0.0:8000 > ../logs/django.log 2>&1 &
DJANGO_PID=$!
echo $DJANGO_PID > ../logs/django.pid
cd ..
sleep 2

if lsof -ti:8000 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Django running (PID: $DJANGO_PID)${NC}"
else
    echo -e "${RED}✗ Django failed to start${NC}"
    exit 1
fi

# Start Celery Worker
echo ""
echo -e "${BLUE}[3/4] Starting Celery Worker...${NC}"
pkill -f "celery.*worker" 2>/dev/null || true
cd backend
source venv/bin/activate
nohup celery -A core worker --loglevel=info --concurrency=2 > ../logs/celery.log 2>&1 &
CELERY_PID=$!
echo $CELERY_PID > ../logs/celery.pid
cd ..
sleep 2
echo -e "${GREEN}✓ Celery running (PID: $CELERY_PID)${NC}"

# Start Frontend
echo ""
echo -e "${BLUE}[4/4] Starting React Frontend...${NC}"
kill $(lsof -ti:3000) 2>/dev/null || true
cd frontend
export PATH="/opt/homebrew/bin:$PATH"
nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../logs/frontend.pid
cd ..
echo -e "${YELLOW}Frontend starting (PID: $FRONTEND_PID)...${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}System Started Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  ✓ Redis:    Port 6379"
echo -e "  ✓ Django:   Port 8000 (PID: $DJANGO_PID)"
echo -e "  ✓ Celery:   Worker (PID: $CELERY_PID)"
echo -e "  ✓ Frontend: Port 3000 (PID: $FRONTEND_PID)"
echo ""
echo -e "${YELLOW}Access:${NC}"
echo -e "  Frontend: ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend:  ${GREEN}http://localhost:8000/api${NC}"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo -e "  tail -f logs/django.log"
echo -e "  tail -f logs/celery.log"
echo -e "  tail -f logs/frontend.log"
echo ""
echo -e "${YELLOW}Stop:${NC}"
echo -e "  ./stop.sh"
echo ""
echo -e "${BLUE}Frontend will be ready in ~30 seconds...${NC}"
echo ""
