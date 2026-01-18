#!/bin/bash
# Stop all RAG System services

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Stopping RAG System${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Stop Frontend
echo -e "${BLUE}Stopping React Frontend...${NC}"
kill $(lsof -ti:3000) 2>/dev/null && echo -e "${GREEN}✓ Frontend stopped${NC}" || echo "  (not running)"
[ -f logs/frontend.pid ] && rm logs/frontend.pid

# Stop Celery
echo -e "${BLUE}Stopping Celery Worker...${NC}"
pkill -f "celery.*worker" 2>/dev/null && echo -e "${GREEN}✓ Celery stopped${NC}" || echo "  (not running)"
[ -f logs/celery.pid ] && rm logs/celery.pid

# Stop Django
echo -e "${BLUE}Stopping Django Backend...${NC}"
kill $(lsof -ti:8000) 2>/dev/null && echo -e "${GREEN}✓ Django stopped${NC}" || echo "  (not running)"
[ -f logs/django.pid ] && rm logs/django.pid

# Note about Redis
echo ""
echo -e "${BLUE}Note:${NC} Redis left running (may be used by other apps)"
echo -e "To stop Redis: ${BLUE}brew services stop redis${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All services stopped${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Logs preserved in ${BLUE}logs/${NC} directory"
echo ""
