# LeRobot Arena Demo

A comprehensive SvelteKit demo application showcasing the LeRobot Arena robotics control platform with real-time 6-DOF robot arm control and monitoring.

## 🚀 Features

### Dashboard
- **Real-time server status monitoring**
- **Active rooms overview**
- **Quick access to all signal types**
- **Clean, modern interface**

### Robotics Control
- **6-DOF robot arm control** with real-time sliders
- **Producer/Consumer pattern** for robot control and monitoring
- **Room management** - create, delete, and join rooms
- **Live joint state monitoring** with trend visualization
- **Command history tracking**
- **Emergency stop functionality**
- **WebSocket-based real-time communication**

### Architecture
- **Frontend**: Svelte 5, TypeScript, Tailwind CSS, Vite
- **Client Library**: Custom TypeScript/JavaScript client
- **Communication**: WebSocket for real-time control, REST API for management
- **Build System**: Bun for fast development and building

## 📁 Project Structure

```
demo/
├── src/
│   ├── routes/
│   │   ├── +layout.svelte           # Main layout with navigation
│   │   ├── +page.svelte             # Dashboard homepage
│   │   ├── robotics/
│   │   │   ├── +page.svelte         # Robotics control dashboard
│   │   │   ├── producer/
│   │   │   │   ├── +page.svelte     # Producer interface
│   │   │   │   └── [roomId]/+page.svelte  # Room-specific producer
│   │   │   └── consumer/
│   │   │       ├── +page.svelte     # Consumer interface
│   │   │       └── [roomId]/+page.svelte  # Room-specific consumer
│   │   └── video/
│   │       └── +page.svelte         # Video placeholder
│   ├── app.css                      # Tailwind CSS and custom styles
│   ├── app.d.ts                     # TypeScript declarations
│   └── app.html                     # HTML template
├── package.json                     # Dependencies and scripts
├── tsconfig.json                    # TypeScript configuration
├── tailwind.config.ts               # Tailwind configuration
├── vite.config.ts                   # Vite configuration
└── test-demo.js                     # Demo verification script
```

## 🛠️ Prerequisites

1. **Bun** >= 1.0.0 ([Install Bun](https://bun.sh/))
2. **LeRobot Arena Server** running on port 8000
3. **Built JavaScript Client** (automatically installed as dependency)

## ⚙️ Server Configuration

The demo automatically detects the correct server URL based on the environment:

- **Development mode**: `http://localhost:8000` (when running on localhost)
- **Production mode**: `https://blanchon-robottransportserver.hf.space/api` (when deployed)

### Environment Variable Override

You can override the default server URL by setting the `PUBLIC_SERVER_URL` environment variable:

```bash
# For development with custom server
export PUBLIC_SERVER_URL=http://localhost:8000

# For production with HuggingFace Space
export PUBLIC_SERVER_URL=https://blanchon-robottransportserver.hf.space/api

# For custom server deployment
export PUBLIC_SERVER_URL=https://your-custom-server.com/api
```

### Setting Environment Variables

#### Option 1: Create a `.env` file
```bash
# In demo/.env
PUBLIC_SERVER_URL=http://localhost:8000
```

#### Option 2: Runtime environment variable
```bash
# Set via window object (for runtime configuration)
window.__SERVER_URL__ = 'http://localhost:8000';
```

#### Option 3: Build-time environment variable
```bash
# When building
PUBLIC_SERVER_URL=https://your-server.com/api bun run build
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd demo
bun install
```

### 2. Start Development Server

```bash
bun run dev
```

The demo will be available at http://localhost:5173

### 3. Test the Setup

```bash
node test-demo.js
```

## 📊 Available Routes

| Route | Description |
|-------|-------------|
| `/` | **Dashboard** - Server status, room overview, quick actions |
| `/robotics` | **Robotics Control** - Room management and overview |
| `/robotics/producer` | **Producer Interface** - Create rooms and control robots |
| `/robotics/consumer` | **Consumer Interface** - Monitor robot state and commands |
| `/robotics/producer/[roomId]` | **Room Producer** - Direct control of specific room |
| `/robotics/consumer/[roomId]` | **Room Consumer** - Direct monitoring of specific room |
| `/video` | **Video Placeholder** - Future video streaming functionality |

## 🎮 Using the Demo

### Dashboard
1. **Monitor server status** - Real-time connection indicator
2. **View active rooms** - See all current robotics sessions
3. **Quick launch** - One-click access to producer/consumer interfaces

### Robot Control (Producer)
1. **Create or join a room**
2. **Control 6-DOF robot arm** with real-time sliders:
   - Base rotation (-180° to 180°)
   - Shoulder movement (-90° to 90°)
   - Elbow movement (-135° to 135°)
   - Wrist 1 rotation (-180° to 180°)
   - Wrist 2 movement (-90° to 90°)
   - Gripper control (0-100%, open to closed)
3. **Send commands** - State sync, emergency stop, heartbeat
4. **Monitor history** - Real-time command tracking

### Robot Monitoring (Consumer)
1. **Connect to existing room**
2. **Live joint monitoring** with trend visualization
3. **Real-time statistics** - Update counts, timing
4. **Command history** - Joint updates and state syncs
5. **Error tracking** - Connection and communication errors

### Room Management
1. **Create rooms** with custom IDs
2. **Delete rooms** when no longer needed
3. **View participants** - Producers and consumers
4. **Monitor activity** - Joint counts and connection status

## 🔧 Development

### Scripts

```bash
# Development server
bun run dev

# Build for production
bun run build

# Preview production build
bun run preview

# Type checking
bun run check

# Linting and formatting
bun run lint
bun run format
```

### Client Library Integration

The demo uses the local `lerobot-arena-client` package:

```typescript
import { robotics } from '@robothub/transport-server-client';

// Create clients
const producer = new robotics.RoboticsProducer('http://localhost:8000');
const consumer = new robotics.RoboticsConsumer('http://localhost:8000');

// Use factory functions
const producer = await robotics.createProducerClient();
const consumer = await robotics.createConsumerClient(roomId);
```

## 🎨 UI/UX Features

### Modern Design
- **Tailwind CSS** for responsive, utility-first styling
- **Custom components** with consistent design system
- **Status indicators** for real-time connection feedback
- **Interactive sliders** for intuitive robot control

### Real-time Feedback
- **Live joint values** with degree precision
- **Trend visualization** showing joint movement history
- **Connection status** with visual indicators
- **Command history** with timestamps and details

### Responsive Layout
- **Mobile-friendly** design for all screen sizes
- **Grid layouts** that adapt to viewport
- **Navigation** with active route highlighting
- **Modal dialogs** for room creation

## 🔒 Safety Features

### Emergency Stop
- **Manual emergency stop** button in producer interface
- **Propagation to all consumers** for immediate notification
- **Error tracking** for safety incident monitoring

### Connection Management
- **Automatic reconnection** handling
- **Timeout configurations** for reliable communication
- **Error reporting** with user-friendly messages

## 🚀 Production Deployment

### Build

```bash
bun run build
```

### Environment Variables

```bash
# Server URL (default: http://localhost:8000)
VITE_SERVER_URL=http://your-server.com:8000
```

### Hosting

The built application can be deployed to any static hosting service:
- Vercel
- Netlify
- GitHub Pages
- AWS S3 + CloudFront
- Any web server

## 🧪 Testing

### Manual Testing

1. **Start the LeRobot Arena server** on port 8000
2. **Run the demo** with `bun run dev`
3. **Test workflows**:
   - Create room as producer
   - Control robot with sliders
   - Connect as consumer in another tab
   - Monitor real-time updates
   - Test emergency stop
   - Verify command history

### Integration Testing

The demo includes integration with the JS client test suite. See `../client/js/tests/` for comprehensive testing.

## 🎯 Use Cases

### Development & Testing
- **Client library testing** - Interactive validation of API
- **Server testing** - Real-time load and functionality testing
- **UI/UX prototyping** - Design validation for robotics interfaces

### Demonstrations
- **Product demos** - Showcase robotics control capabilities
- **Educational tool** - Learn producer/consumer patterns
- **Integration examples** - Reference implementation for developers

### Real-world Applications
- **Remote robot control** - Control robots from anywhere
- **Multi-user collaboration** - Multiple operators monitoring one robot
- **Training simulations** - Safe environment for learning robot control

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make changes** and add tests
4. **Run linting** (`bun run lint`)
5. **Test thoroughly** with demo application
6. **Commit changes** (`git commit -m 'Add amazing feature'`)
7. **Push to branch** (`git push origin feature/amazing-feature`)
8. **Open Pull Request**

## 📝 License

MIT License - see LICENSE file for details

---

## 🆘 Troubleshooting

### Connection Issues
- **Server not running**: Ensure LeRobot Arena server is active on port 8000
- **CORS errors**: Check server CORS configuration
- **WebSocket failures**: Verify firewall settings

### Build Issues
- **Import errors**: Ensure client library is built (`cd ../client/js && bun run build`)
- **Type errors**: Run `bun run check` for detailed TypeScript diagnostics
- **Dependency issues**: Try `rm -rf node_modules && bun install`

### Runtime Issues
- **Slow performance**: Check browser dev tools for console errors
- **UI not updating**: Verify WebSocket connection in network tab
- **Commands not working**: Check server logs for error messages

For more help, see the main project documentation or open an issue on GitHub.
