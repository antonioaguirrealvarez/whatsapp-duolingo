# WhatsApp Duolingo - AI Language Learning Bot

An AI-powered WhatsApp language learning bot that provides Duolingo-style lessons with personalized tutoring.

## 🎯 Features

### Phase I (✅ Complete - Skeleton)
- **WhatsApp Integration**: Receive and send messages via WhatsApp API
- **LLM Integration**: Basic AI responses for language learning
- **Session Management**: Track user state and progress
- **Basic Error Handling**: Graceful failure recovery

### Phase II (✅ Complete - Brain)
- **Smart Onboarding**: Simplified new user setup (Portuguese→English B1 by default)
- **Real Lessons**: Database-driven exercises with LLM fallback
- **Tutor Flow**: Interactive lesson sessions with answer evaluation
- **Progress Tracking**: User performance and completion metrics

### Phase III (🚧 Planned - Monetization)
- **Subscription Management**: Premium features and billing
- **Advanced Analytics**: Detailed learning insights
- **Multi-language Support**: Expand beyond Portuguese→English

### Phase IV (📋 Future - Growth)
- **Multimodal Learning**: Voice, images, and interactive content
- **Social Features**: Leaderboards and community learning
- **Advanced AI**: Personalized curriculum generation

## 🏗️ Architecture

```
src/
├── orchestrator/           # Core message processing and flow control
│   ├── core.py            # Main event orchestrator
│   ├── flows/             # Conversation flows (onboarding, lessons)
│   └── session_manager.py # User session state management
├── services/              # External service integrations
│   ├── llm/              # AI/LLM gateway and content generation
│   ├── whatsapp/         # WhatsApp API client
│   └── validation/       # Exercise answer evaluation
├── data/                  # Database layer
│   ├── models.py         # SQLAlchemy models
│   ├── repositories/     # Data access layer
│   └── migrations/       # Database schema migrations
└── core/                  # Shared utilities and configuration
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL (for production) or SQLite (for development)
- WhatsApp Business API access
- OpenAI API key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/antonioaguirrealvarez/whatsapp-duolingo.git
cd whatsapp-duolingo
```

2. **Set up virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Initialize database**
```bash
alembic upgrade head
```

6. **Start the server**
```bash
uvicorn src.main:app --reload
```

## 🧪 Testing

Run the test suite:
```bash
# All tests
pytest

# Specific test categories
pytest tests/e2e/          # End-to-end tests
pytest tests/unit/         # Unit tests
pytest tests/integration/  # Integration tests
```

### Test Coverage
- ✅ **E2E Tests**: 18/18 passing (onboarding, lessons, full flow)
- ✅ **Unit Tests**: 80/80 passing (core functionality)
- ✅ **Integration Tests**: 22/23 passing (database, services)

## 📱 Usage

### For New Users
1. Send "Hi" to the WhatsApp bot
2. Receive automatic onboarding setup
3. Start lessons with "start lesson"

### For Existing Users
1. Send "start lesson" to begin practice
2. Answer exercises via text responses
3. Get immediate feedback and explanations

### Commands
- `start lesson` - Begin a new lesson
- `help` - Show available commands
- `progress` - View learning progress

## 🔧 Development

### Project Structure
- **TDD Approach**: Test-driven development with comprehensive test coverage
- **Atomic Commits**: Small, focused changes with clear commit messages
- **Feature Flags**: Easy toggle for experimental features

### Key Components

#### Orchestrator Core
- **Event Processing**: Handles incoming WhatsApp messages
- **Flow Delegation**: Routes to appropriate conversation flows
- **Session Management**: Maintains user context and state

#### Chat Flows
- **Onboarding Flow**: Simplified setup for new users
- **Tutor Flow**: Interactive lesson sessions
- **Error Recovery**: Graceful handling of failures

#### Data Layer
- **Exercise Repository**: Database-driven content management
- **User Progress**: Performance tracking and analytics
- **Session Storage**: In-memory session persistence

## 📊 Current Status

### Phase II Complete ✅
- [x] Orchestrator integration with ChatFlow
- [x] Simplified onboarding (Portuguese→English B1)
- [x] Real lesson functionality with database exercises
- [x] LLM fallback for exercise generation
- [x] Comprehensive test coverage
- [x] Vestigial code cleanup

### Next Steps (Phase III)
- [ ] Subscription management system
- [ ] Advanced user analytics
- [ ] Multi-language expansion
- [ ] Performance optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow TDD principles
- Write comprehensive tests
- Keep commits atomic and well-documented
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Duolingo** - Inspiration for the learning approach
- **OpenAI** - AI/LLM capabilities
- **WhatsApp** - Platform for bot deployment
- **FastAPI** - High-performance web framework

## 📞 Support

For questions, issues, or contributions:
- 📧 Create an issue on GitHub
- 💬 Join our development discussions
- 📖 Check the documentation

---

**Built with ❤️ for language learners everywhere**
