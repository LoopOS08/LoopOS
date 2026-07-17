# LoopOS

Connective Intelligence Layer for SMB Operations

## Overview

LoopOS is a connective intelligence layer designed for 10-100 person companies that turns organizational artifacts into a self-improving closed loop system. The platform connects fragmented SaaS tools into a unified queryable, learning, and autonomous system.

## Architecture

LoopOS is built around a five-layer architecture:

1. **Integration Layer** - Webhook receivers, API connectors, OAuth vault
2. **Artifact Store** - Every company artifact stored, indexed, and embedded
3. **Intelligence Layer** - Cross-tool reasoning, semantic search, decision extraction
4. **Agent Layer** - 7 specialized agents monitoring and acting autonomously
5. **Flywheel Engine** - Learns from outcomes and improves agents

## Technology Stack

- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: Python 3.11 + FastAPI + Celery + Redis
- **Database**: PostgreSQL 16 + pgvector + Supabase
- **Authentication**: Clerk + Row-Level Security
- **AI**: Claude 3.5 Sonnet + GPT-4o + Groq Llama 3
- **Infrastructure**: Vercel + Railway + Modal + Upstash

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 16 with pgvector extension
- Redis
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd loopOS
```

2. Install dependencies:
```bash
# Install root dependencies
npm install

# Install backend dependencies
cd apps/backend
poetry install
cd ../..

# Install frontend dependencies
cd apps/frontend
npm install
cd ../..
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
# Using Docker Compose (recommended)
docker-compose up postgres redis
```

5. Run the development servers:
```bash
# Terminal 1 - Backend
cd apps/backend
poetry run uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd apps/frontend
npm run dev
```

### Using Docker Compose

For a complete development environment with all services:

```bash
docker-compose up
```

This will start:
- PostgreSQL with pgvector extension
- Redis for caching and task queues
- FastAPI backend on port 8000
- Next.js frontend on port 3000

## Project Structure

```
loopOS/
├── apps/
│   ├── frontend/          # Next.js frontend application
│   └── backend/           # FastAPI backend application
├── packages/
│   ├── types/            # Shared TypeScript types
│   └── shared/           # Shared utilities
├── docker-compose.yml    # Development environment
├── turbo.json           # Turborepo configuration
└── package.json         # Root package.json
```

## Development

### Running Tests

```bash
# Run all tests
npm run test

# Run backend tests
cd apps/backend
poetry run pytest

# Run frontend tests
cd apps/frontend
npm test
```

### Building

```bash
# Build all packages
npm run build

# Build specific package
cd apps/frontend
npm run build
```

### Linting

```bash
# Lint all packages
npm run lint

# Format code
npm run format
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Phase 1 Status

✅ Monorepo Setup  
✅ Database Schema with pgvector  
✅ Row-Level Security (RLS)  
✅ FastAPI Backend  
✅ Authentication Framework  
✅ OAuth Integration Framework  
✅ Credential Security Service  
✅ Agent Base Class  
✅ Encryption Service  

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## License

Proprietary - All rights reserved