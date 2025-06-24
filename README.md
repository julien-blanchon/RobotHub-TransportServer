---
title: LeRobot Arena Transport Server
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
dockerfile_path: services/transport-server/Dockerfile
suggested_hardware: cpu-upgrade
suggested_storage: small
short_description: Real-time robotics control 
tags:
  - robotics
  - control
  - websocket
  - fastapi
  - svelte
  - real-time
  - video-streaming
  - transport-server
pinned: true
fullWidth: true
---

# 🤖 LeRobot Arena Transport Server with UI

A complete Docker deployment of the LeRobot Arena Transport Server with integrated web UI. This combines the FastAPI backend with a SvelteKit frontend in a single container, inspired by the [LeRobot Arena Hugging Face Space](https://huggingface.co/spaces/blanchon/LeRobot-Arena).

## 🚀 Quick Start with Docker

The easiest way to run the complete LeRobot Arena Transport Server is using Docker, which sets up both the frontend and backend automatically.

### Prerequisites

- [Docker](https://www.docker.com/get-started) installed on your system
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

### Step-by-Step Instructions

1. **Navigate to the transport server directory**
   ```bash
   cd services/transport-server
   ```

2. **Build the Docker image**
   ```bash
   docker build -t lerobot-arena-transport .
   ```

3. **Run the container**
   ```bash
   docker run -p 7860:7860 -e SERVE_FRONTEND=true lerobot-arena-transport
   ```

4. **Access the application**
   - **Frontend**: http://localhost:7860
   - **Backend API**: http://localhost:7860/api
   - **API Documentation**: http://localhost:7860/api/docs

5. **Stop the container**
   ```bash
   # Find the container ID
   docker ps
   
   # Stop the container
   docker stop <container_id>
   ```

### Alternative Build & Run Options

**One-liner build and run:**
```bash
docker build -t lerobot-arena-transport . && docker run -p 7860:7860 -e SERVE_FRONTEND=true lerobot-arena-transport
```

**Run with custom environment variables:**
```bash
docker run -p 8080:7860 \
  -e SERVE_FRONTEND=true \
  -e PORT=7860 \
  -e HOST=0.0.0.0 \
  lerobot-arena-transport
```

**Run with volume mounts for logs:**
```bash
docker run -p 7860:7860 \
  -e SERVE_FRONTEND=true \
  -v $(pwd)/logs:/home/user/app/logs \
  lerobot-arena-transport
```

## 🛠️ Development Setup

For local development with hot-reload capabilities:

### Backend Development

```bash
# Navigate to server directory
cd server

# Install Python dependencies (using uv)
uv sync

# Start the backend server only
python api.py
```

### Frontend Development

```bash
# Navigate to demo directory
cd demo

# Install dependencies
bun install

# Start the development server
bun run dev
```

### Client Library Development

```bash
# Navigate to client library
cd client/js

# Install dependencies
bun install

# Build the client library
bun run build
```

## 📋 Project Structure

```
services/transport-server/
├── server/                     # Python FastAPI backend
│   ├── src/                   # Source code
│   ├── api.py                 # Main API application
│   ├── launch_with_ui.py      # Combined launcher
│   └── pyproject.toml         # Python dependencies
├── demo/                      # SvelteKit frontend
│   ├── src/                   # Frontend source code
│   ├── package.json           # Node.js dependencies
│   └── svelte.config.js       # SvelteKit configuration
├── client/js/                 # TypeScript client library
│   ├── src/                   # Client library source
│   └── package.json           # Client dependencies
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose setup
└── README.md                  # This file
```

## 🐳 Docker Information

The Docker setup includes:

- **Multi-stage build**: Optimized for production using Bun and uv
- **Client library build**: Builds the TypeScript client first
- **Frontend build**: Compiles SvelteKit app to static files
- **Backend integration**: FastAPI serves both API and static files
- **Port mapping**: Single port 7860 for both frontend and API
- **User permissions**: Properly configured for Hugging Face Spaces
- **Environment variables**: Configurable via environment

### Environment Variables

- `SERVE_FRONTEND=true`: Enable frontend serving (default: false)
- `PORT=7860`: Port to run the server on (default: 7860)
- `HOST=0.0.0.0`: Host to bind to (default: 0.0.0.0)

## 🌐 What's Included

### Backend Features
- **Real-time Robot Control**: WebSocket-based communication
- **Video Streaming**: WebRTC video streaming capabilities
- **REST API**: Complete robotics control API
- **Room Management**: Create and manage robot control sessions
- **Health Monitoring**: Built-in health checks and logging

### Frontend Features
- **Dashboard**: Server status and room overview
- **Robot Control**: 6-DOF robot arm control interface
- **Real-time Monitoring**: Live joint state visualization
- **Workspace Management**: Isolated environments for different sessions
- **Modern UI**: Responsive design with Tailwind CSS

### Architecture
- **Frontend**: Svelte 5, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.12, uvicorn
- **Client Library**: TypeScript with WebSocket support
- **Build System**: Bun for frontend, uv for Python
- **Container**: Multi-stage Docker build

## 🔧 API Endpoints

### Health Check
- `GET /health` - Server health status
- `GET /api/health` - API health status

### Robotics API
- `GET /api/robotics/rooms` - List active rooms
- `POST /api/robotics/rooms` - Create new room
- `DELETE /api/robotics/rooms/{room_id}` - Delete room
- `WebSocket /api/robotics/ws/{room_id}` - Real-time control

### Video API
- `GET /api/video/rooms` - List video rooms
- `WebSocket /api/video/ws/{room_id}` - Video streaming

## 🧪 Testing the Setup

Run the included test script to verify everything works:

```bash
./test-docker.sh
```

This script will build the image, start a container, test all endpoints, and clean up automatically.

## 🚨 Troubleshooting

### Port Conflicts
If port 7860 is already in use:

```bash
# Check what's using the port
lsof -i :7860

# Use different port
docker run -p 8080:7860 -e SERVE_FRONTEND=true lerobot-arena-transport
```

### Container Issues

```bash
# View logs
docker logs <container_id>

# Rebuild without cache
docker build --no-cache -t lerobot-arena-transport .

# Run with verbose logging
docker run -p 7860:7860 -e SERVE_FRONTEND=true -e LOG_LEVEL=debug lerobot-arena-transport
```

### Development Issues

```bash
# Clear node modules and reinstall (for local development)
cd demo
rm -rf node_modules
bun install

# Clear SvelteKit cache
rm -rf .svelte-kit
bun run dev

# Re-link client library (if needed for local development)
cd ../client/js
bun link
cd ../../demo
bun link lerobot-arena-client
```

### Client Library Issues

```bash
# Rebuild client library
cd client/js
bun run clean
bun run build
```

## 🚀 Hugging Face Spaces Deployment

This project is configured for deployment on Hugging Face Spaces:

1. **Fork** this repository to your GitHub account
2. **Create a new Space** on Hugging Face Spaces
3. **Connect** your GitHub repository
4. **Select Docker SDK** (should be auto-detected)
5. **Set the Dockerfile path** to `services/transport-server/Dockerfile`
6. **Deploy**

The Space will automatically build and run both the frontend and backend.

### Hugging Face Spaces Configuration

Add this to your Space's README.md frontmatter:

```yaml
---
title: LeRobot Arena Transport Server
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
dockerfile_path: services/transport-server/Dockerfile
suggested_hardware: cpu-upgrade
suggested_storage: small
short_description: Real-time robotics control and video streaming
tags:
  - robotics
  - control
  - websocket
  - fastapi
  - svelte
pinned: true
fullWidth: true
---
```

## 🎯 Use Cases

### Development & Testing
- **API Development**: Test robotics control APIs
- **Frontend Development**: Develop robotics UIs
- **Integration Testing**: Test real-time communication

### Production Deployment
- **Robot Control**: Remote robot operation
- **Multi-user**: Multiple operators on same robot
- **Monitoring**: Real-time robot state monitoring

### Education & Demos
- **Learning**: Robotics programming education
- **Demonstrations**: Showcase robotics capabilities
- **Prototyping**: Rapid robotics application development

## 🤝 Contributing

1. **Fork** the repository
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make changes** and add tests
4. **Test with Docker** (`./test-docker.sh`)
5. **Commit changes** (`git commit -m 'Add amazing feature'`)
6. **Push to branch** (`git push origin feature/amazing-feature`)
7. **Open Pull Request**

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ for the robotics community** 🤖

For more information, visit the [main LeRobot Arena project](https://github.com/lerobot-arena/lerobot-arena). 