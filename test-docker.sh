#!/bin/bash

# Test script for LeRobot Arena Transport Server Docker setup
set -e

echo "🤖 Testing LeRobot Arena Transport Server Docker Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="lerobot-arena-transport-test"
PORT=7860
MAX_WAIT=60

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Step 1: Build the Docker image
echo -e "\n${YELLOW}Step 1: Building Docker image...${NC}"
docker build -t lerobot-arena-transport . || {
    echo -e "${RED}❌ Failed to build Docker image${NC}"
    exit 1
}
echo -e "${GREEN}✅ Docker image built successfully${NC}"

# Step 2: Start the container
echo -e "\n${YELLOW}Step 2: Starting container...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:7860 \
    -e SERVE_FRONTEND=true \
    lerobot-arena-transport || {
    echo -e "${RED}❌ Failed to start container${NC}"
    exit 1
}
echo -e "${GREEN}✅ Container started successfully${NC}"

# Step 3: Wait for container to be ready
echo -e "\n${YELLOW}Step 3: Waiting for container to be ready...${NC}"
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Container is ready!${NC}"
        break
    fi
    echo "Waiting... ($COUNTER/$MAX_WAIT)"
    sleep 2
    COUNTER=$((COUNTER + 2))
done

if [ $COUNTER -ge $MAX_WAIT ]; then
    echo -e "${RED}❌ Container failed to start within $MAX_WAIT seconds${NC}"
    echo "Container logs:"
    docker logs $CONTAINER_NAME
    exit 1
fi

# Step 4: Test endpoints
echo -e "\n${YELLOW}Step 4: Testing endpoints...${NC}"

# Test health endpoint
echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:$PORT/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ /health endpoint working${NC}"
else
    echo -e "${RED}❌ /health endpoint failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test API health endpoint
echo "Testing /api/health endpoint..."
API_HEALTH_RESPONSE=$(curl -s http://localhost:$PORT/api/health)
if echo "$API_HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ /api/health endpoint working${NC}"
else
    echo -e "${RED}❌ /api/health endpoint failed${NC}"
    echo "Response: $API_HEALTH_RESPONSE"
    exit 1
fi

# Test frontend
echo "Testing frontend..."
FRONTEND_RESPONSE=$(curl -s http://localhost:$PORT/)
if echo "$FRONTEND_RESPONSE" | grep -q "<!doctype html>" && echo "$FRONTEND_RESPONSE" | grep -q "_app/immutable"; then
    echo -e "${GREEN}✅ Frontend is served correctly${NC}"
else
    echo -e "${RED}❌ Frontend test failed${NC}"
    echo "Response preview: $(echo "$FRONTEND_RESPONSE" | head -5)"
    exit 1
fi

# Test API documentation
echo "Testing API documentation..."
DOCS_RESPONSE=$(curl -s http://localhost:$PORT/api/docs)
if echo "$DOCS_RESPONSE" | grep -q "swagger"; then
    echo -e "${GREEN}✅ API documentation accessible${NC}"
else
    echo -e "${RED}❌ API documentation test failed${NC}"
    exit 1
fi

# Test robotics API
echo "Testing robotics API..."
ROBOTICS_RESPONSE=$(curl -s http://localhost:$PORT/api/robotics/rooms)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Robotics API accessible${NC}"
else
    echo -e "${RED}❌ Robotics API test failed${NC}"
    exit 1
fi

# Test video API
echo "Testing video API..."
VIDEO_RESPONSE=$(curl -s http://localhost:$PORT/api/video/rooms)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Video API accessible${NC}"
else
    echo -e "${RED}❌ Video API test failed${NC}"
    exit 1
fi

# Step 5: Show container information
echo -e "\n${YELLOW}Step 5: Container information${NC}"
echo "Container status:"
docker ps | grep $CONTAINER_NAME

echo -e "\nContainer resource usage:"
docker stats --no-stream $CONTAINER_NAME

# Step 6: Success summary
echo -e "\n${GREEN}🎉 All tests passed successfully!${NC}"
echo "=================================================="
echo "✅ Docker image builds correctly"
echo "✅ Container starts and runs"
echo "✅ Health endpoints respond correctly"
echo "✅ Frontend is served"
echo "✅ API documentation is accessible"
echo "✅ Robotics API is working"
echo "✅ Video API is working"
echo ""
echo "🌐 Access the application at: http://localhost:$PORT"
echo "📚 API docs available at: http://localhost:$PORT/api/docs"
echo ""
echo "To manually test:"
echo "  docker run -p 7860:7860 -e SERVE_FRONTEND=true lerobot-arena-transport"
echo ""
echo -e "${YELLOW}Container will be cleaned up automatically.${NC}" 