# CivicForge Prototype

This is a minimal viable prototype demonstrating the core Civic Compass concept: a Local Controller (on your device) communicating with a Remote Thinker (AI service) to facilitate civic engagement through natural conversation.

## What This Demonstrates

1. **Hybrid Agent Model**: Separation between local control and remote intelligence
2. **Natural Language Interface**: Talk naturally instead of filling forms
3. **Approval Flow**: Local Controller maintains final authority over actions
4. **Privacy by Design**: User explicitly approves what data is shared

## Quick Start

### Prerequisites

- Python 3.7+ (for Remote Thinker)
- Node.js 14+ (for Local Controller)

### Quickest Start: Use the Demo Script

```bash
cd prototype
./demo.sh
```

This will automatically install dependencies, start both components, and handle cleanup when you're done.

### 1. Install Dependencies

```bash
# Install FastAPI for the Remote Thinker
pip install fastapi uvicorn

# No npm dependencies needed for Local Controller (uses built-in Node modules)
```

### 2. Start the Remote Thinker

In one terminal:

```bash
cd prototype
python remote_thinker.py
```

You should see:
```
Starting CivicForge Remote Thinker prototype...
API documentation will be available at http://localhost:8000/docs
```

### 3. Start the Local Controller

In another terminal:

```bash
cd prototype
node local_controller.js
```

You should see:
```
🔄 Connecting to Remote Thinker...
✅ Connected to Remote Thinker!

🏛️  Welcome to CivicForge - Your Civic Compass
================================================
```

## Try These Conversations

```
You: I have some free time this weekend and want to help

You: I'm interested in teaching or mentoring

You: I care about the environment

You: I'd like to help seniors in my community
```

## Architecture Overview

```
┌─────────────────────┐         ┌──────────────────────┐
│  Local Controller   │  HTTP   │   Remote Thinker     │
│  (local_controller) │ <-----> │  (remote_thinker.py) │
│                     │         │                      │
│ - User interface    │         │ - NLU (simulated)    │
│ - Approval flow     │         │ - Opportunity DB     │
│ - Privacy control   │         │ - Action proposals   │
└─────────────────────┘         └──────────────────────┘
```

## Key Files

- `remote_thinker.py`: FastAPI server simulating the AI service
- `local_controller.js`: CLI interface demonstrating local control
- `README.md`: This file

## Next Steps

This prototype demonstrates the core concept. Future development would add:

1. **Real NLU**: Replace keyword matching with actual language models
2. **Persistent Storage**: Add database for opportunities and user preferences  
3. **Authentication**: Implement DID-based identity
4. **Mobile App**: Replace CLI with React Native app
5. **P2P Discovery**: Add federated network capabilities

## API Documentation

While the Remote Thinker is running, visit http://localhost:8000/docs for interactive API documentation.

## Contributing

See the main [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on expanding this prototype.