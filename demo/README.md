# RobotHub TransportServer Demo

A simple SvelteKit demo application for visualizing and debugging the RobotHub TransportServer platform. This web interface helps verify that the server and client libraries are working correctly.

## 🎯 Purpose

This demo is a **development and testing tool** that provides:

- **Visual interface** to test robotics control and video streaming
- **Connection verification** for WebSocket and WebRTC functionality  
- **Debugging tool** to monitor real-time communication
- **Example implementation** showing how to use the client libraries

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ or Bun
- Running RobotHub TransportServer

### Setup & Run

```bash
# Install dependencies
bun install

# Start development server
bun run dev

# Open http://localhost:5173
```

## 🖥️ Interface

### Workspace Management
- Create isolated test environments
- Join existing workspaces for collaborative testing

### Robotics Testing
- **Producer**: Send joint commands with sliders
- **Consumer**: Monitor received commands in real-time
- **Emergency Stop**: Test safety mechanisms

### Video Testing  
- **Producer**: Test camera and screen sharing
- **Consumer**: Verify video stream reception
- **Multi-stream**: Test multiple concurrent streams

## 🔧 Configuration

Default server endpoints:
```typescript
const CONFIG = {
  transportServerUrl: 'http://localhost:8000',
  wsServerUrl: 'ws://localhost:8000'
};
```

Override with environment variables:
```bash
PUBLIC_TRANSPORT_SERVER_URL=http://your-server:8000
PUBLIC_WS_SERVER_URL=ws://your-server:8000
```

## 🛠️ Development

```bash
# Development
bun run dev

# Build
bun run build

# Preview
bun run preview
```

---

**This demo helps you verify everything works!** 🤖✨
