# Personal TimeBox

A comprehensive Django-based personal time management application that implements the timeboxing method to help users improve productivity, track goals, and build better habits.

## 🎯 Features

### Core Timeboxing
- **Task Management**: Create, edit, and organize tasks with categories, priorities, and energy levels
- **Time Tracking**: Start, pause, and complete focused work sessions with detailed analytics
- **Session Management**: Track actual vs planned time, focus ratings, and productivity metrics
- **Real-time Progress**: Live updates and progress tracking during active sessions

### Goal Setting & Tracking
- **Personal Goals**: Set goals with target hours and time periods (daily, weekly, monthly, etc.)
- **Progress Monitoring**: Visual progress tracking and achievement notifications
- **Goal Analytics**: Track completion rates and time spent on goal-related activities

### Habit Building
- **Habit Tracking**: Create and track daily, weekly, or monthly habits
- **Habit Logging**: Daily check-ins with notes and completion status
- **Habit Analytics**: Track consistency and streaks over time

### Advanced Analytics
- **Productivity Dashboard**: Comprehensive overview of sessions, tasks, and goals
- **Time Analysis**: Detailed breakdown of time spent across categories and activities
- **Performance Metrics**: Focus ratings, energy levels, and efficiency scores
- **Export Functionality**: Export data to CSV/JSON for further analysis

### Personalization
- **Custom Categories**: Create personalized task categories with colors and icons
- **User Preferences**: Customize work durations, break times, and notification settings
- **Daily Reflections**: End-of-day reviews with mood, energy, and productivity tracking
- **Weekly Reviews**: Comprehensive weekly summaries and improvement planning

### Data Management
- **Export/Import**: Full data export in multiple formats (CSV, JSON)
- **Data Privacy**: Complete control over personal data with local storage options
- **Backup & Recovery**: Regular data backups and easy recovery options

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL (recommended) or SQLite for development
- Redis (for Celery background tasks)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/arazshah/timeboxing.git
   cd timeboxing
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DATABASE_URL=sqlite:///db.sqlite3  # or PostgreSQL URL
   REDIS_URL=redis://localhost:6379/0
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   EMAIL_USE_TLS=True
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Start the development server**
   ```bash
   python manage.py runserver
   ```

Visit `http://localhost:8000` to access the application.

## 📊 Database Schema

### Core Models
- **User**: Django's built-in user model with custom preferences
- **PersonalCategory**: Task categories with types, colors, and icons
- **PersonalTask**: Tasks with priorities, energy levels, and time estimates
- **PersonalGoal**: Goals with target hours and time periods
- **PersonalTimeboxSession**: Individual work sessions with detailed metrics
- **PersonalHabit**: Habits with frequency and tracking
- **HabitLog**: Daily habit completion records
- **DailyReflection**: End-of-day reviews and reflections
- **WeeklyReview**: Weekly summaries and planning
- **UserPreferences**: Customizable user settings

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DATABASE_URL` | Database connection URL | SQLite |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `EMAIL_HOST` | SMTP server for emails | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | Email username | Required |
| `EMAIL_HOST_PASSWORD` | Email password | Required |

### Celery Configuration

The application uses Celery for background tasks:
- **Email notifications** for overdue tasks
- **Periodic tasks** for data cleanup and analytics
- **Scheduled reports** and reminders

To start Celery worker:
```bash
celery -A timebox_project worker --loglevel=info
```

To start Celery beat scheduler:
```bash
celery -A timebox_project beat --loglevel=info
```

## 🎨 Frontend

### Technologies Used
- **HTML5** with Django template engine
- **CSS3** with custom styling and Bootstrap integration
- **JavaScript** for interactive features
- **Django Crispy Forms** for form rendering
- **Widget Tweaks** for form customization

### Key Features
- Responsive design for mobile and desktop
- Real-time session updates
- Interactive charts and analytics
- Drag-and-drop task organization
- Live search and filtering

## 📱 API Endpoints

The application includes REST API endpoints for:
- Task management (CRUD operations)
- Session tracking and analytics
- Goal progress monitoring
- Data export functionality

API documentation is available at `/api/docs/` when DEBUG is enabled.

## 🚀 Deployment

### Production Setup

1. **Environment Configuration**
   ```env
   DEBUG=False
   SECRET_KEY=your-production-secret-key
   ALLOWED_HOSTS=yourdomain.com
   DATABASE_URL=postgresql://user:password@localhost/dbname
   ```

2. **Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Database Optimization**
   ```bash
   python manage.py migrate
   python manage.py createcachetable
   ```

4. **Gunicorn Configuration**
   ```bash
   gunicorn timebox_project.wsgi:application --bind 0.0.0.0:8000
   ```

### Docker Deployment

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "timebox_project.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Environment-specific Settings

- **Development**: SQLite database, debug mode enabled
- **Production**: PostgreSQL database, static files served by Nginx
- **Testing**: In-memory database, minimal configuration

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test personal_timebox

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Test Coverage
- Unit tests for all models and views
- Integration tests for user workflows
- API endpoint testing
- Form validation testing

## 📈 Monitoring & Analytics

### Built-in Analytics
- **Session Analytics**: Time spent, focus ratings, efficiency scores
- **Task Analytics**: Completion rates, priority distribution, category breakdown
- **Goal Analytics**: Progress tracking, achievement rates, time allocation
- **Habit Analytics**: Consistency tracking, streak analysis, completion rates

### Performance Monitoring
- **Django Debug Toolbar** for development
- **Sentry integration** for error tracking
- **Application metrics** and logging

## 🔒 Security

### Security Features
- **User Authentication**: Django's built-in authentication system
- **Password Security**: Hashed passwords with bcrypt
- **CSRF Protection**: Cross-site request forgery protection
- **XSS Prevention**: Cross-site scripting prevention
- **SQL Injection Protection**: Django ORM parameterized queries
- **HTTPS Enforcement**: SSL/TLS encryption in production

### Data Privacy
- **Local Storage**: All data stored locally by default
- **Export Control**: Users can export and delete their data
- **Anonymous Analytics**: Optional anonymous usage statistics
- **GDPR Compliance**: Data protection and user rights

## 🤝 Contributing

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Run tests**
   ```bash
   python manage.py test
   ```
5. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
6. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Coding Standards
- **Python**: Follow PEP 8 style guide
- **Django**: Follow Django best practices
- **JavaScript**: Use ES6+ features
- **CSS**: Use BEM methodology
- **Documentation**: Include docstrings and comments

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Django Team** for the excellent web framework
- **Bootstrap** for the UI components
- **Celery** for background task processing
- **Redis** for caching and message broker
- **PostgreSQL** for the robust database

## 📞 Support

For support, please open an issue on GitHub or contact the development team.

### Bug Reports
- Use GitHub Issues for bug reports
- Include steps to reproduce the issue
- Provide error messages and stack traces
- Specify your environment (OS, Python version, etc.)

### Feature Requests
- Use GitHub Issues for feature requests
- Describe the use case and expected behavior
- Provide examples and mockups if applicable

## 🎯 Roadmap

### Upcoming Features
- [ ] Mobile app (React Native)
- [ ] Advanced reporting and analytics
- [ ] Team collaboration features
- [ ] Integration with calendar applications
- [ ] AI-powered productivity insights
- [ ] Voice commands and speech-to-text
- [ ] Offline mode support
- [ ] Advanced habit tracking with streaks
- [ ] Goal templates and suggestions
- [ ] Time blocking visualization

### Version History

#### v1.0.0 (Current)
- Core timeboxing functionality
- Task and goal management
- Habit tracking
- Basic analytics
- Data export features

#### v0.9.0
- Initial development version
- Basic task management
- Simple time tracking

---

**Built with ❤️ using Django and modern web technologies**

## 👨‍💻 Author

**Araz Shahkarami**

- 🌐 Website: [www.araz.me](https://www.araz.me)
- 📱 Telegram: [@arazshah](https://t.me/arazshah)
