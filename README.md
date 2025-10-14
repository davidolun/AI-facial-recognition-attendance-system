# AI-Powered Attendance Management System

[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-red.svg)](https://opencv.org/)
[![TensorFlow.js](https://img.shields.io/badge/TensorFlow.js-4.10+-orange.svg)](https://www.tensorflow.org/js)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A cutting-edge, full-stack attendance tracking system that leverages computer vision, machine learning, and AI to revolutionize educational attendance management. Built with Django, featuring real-time face recognition, predictive analytics, and an intelligent AI assistant.

## 🚀 Key Highlights

- **Real-time Face Recognition**: Automated attendance using OpenCV and face_recognition library
- **AI-Powered Analytics**: TensorFlow.js-based predictive modeling and risk assessment
- **Intelligent Assistant**: OpenAI GPT-4o-mini integration for natural language queries
- **Multi-User Architecture**: Role-based access for teachers and administrators
- **Advanced Visualizations**: Interactive charts with Chart.js and D3.js
- **Production-Ready**: Scalable design with proper error handling and security

## 🏗️ Architecture Overview

```
├── Face Recognition Pipeline
│   ├── Real-time Detection (OpenCV)
│   ├── Feature Extraction (face_recognition)
│   └── Database Matching
├── AI Analytics Engine
│   ├── Predictive Modeling (TensorFlow.js)
│   ├── Pattern Recognition
│   └── Risk Assessment
├── Intelligent Assistant
│   ├── Natural Language Processing (OpenAI)
│   ├── Context-Aware Responses
│   └── Data Filtering
└── Multi-Tenant System
    ├── User Management (Django Auth)
    ├── Class/Session Management
    └── Data Isolation
```

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 4.2+
- **Database**: PostgreSQL (recommended) / SQLite (development)
- **API**: Django REST Framework
- **Authentication**: Django's built-in auth with custom User model

### Frontend
- **Core**: HTML5, CSS3, JavaScript (ES6+)
- **Visualization**: Chart.js, D3.js
- **Machine Learning**: TensorFlow.js
- **Styling**: Custom CSS with responsive design

### AI & Computer Vision
- **Face Recognition**: face_recognition library (dlib backend)
- **Image Processing**: OpenCV, NumPy
- **NLP**: OpenAI GPT-4o-mini API
- **Predictive Analytics**: Custom ML models in TensorFlow.js

### Infrastructure
- **Deployment**: Docker-ready configuration
- **Version Control**: Git
- **Package Management**: pip, requirements.txt

## ✨ Features

### 🔍 Face Recognition System
- **Real-time Detection**: Processes live video streams for face detection
- **Student Enrollment**: Secure image capture and encoding storage
- **Attendance Logging**: Automatic timestamp recording with late arrival detection
- **Accuracy Optimization**: Handles varying lighting and angles

### 🤖 AI-Powered Analytics
- **Predictive Modeling**: 7-day attendance forecasting with confidence intervals
- **Risk Assessment**: ML-based identification of at-risk students
- **Pattern Recognition**: Clustering analysis of attendance behaviors
- **Time Series Analysis**: Seasonal trends and anomaly detection
- **Correlation Analysis**: Feature importance and relationship mapping

### 💬 Intelligent Assistant
- **Natural Language Queries**: Ask questions like "Who was absent last week?"
- **Context Awareness**: Maintains conversation history for follow-up questions
- **Data Filtering**: Teacher-specific responses based on permissions
- **Real-time Insights**: Instant analysis of attendance patterns

### 👥 Multi-User Management
- **Role-Based Access**: Teachers and administrators with different permissions
- **Class Management**: Create and manage classes with student assignments
- **Session Tracking**: Organize attendance by class sessions and dates
- **Data Privacy**: Secure isolation of teacher-specific data

### 📊 Advanced Dashboard
- **Interactive Charts**: Multiple visualization types for comprehensive insights
- **Real-time Updates**: Live data refresh with AJAX calls
- **Export Functionality**: CSV export for reporting and analysis
- **Responsive Design**: Optimized for desktop and mobile devices

## 📋 Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git
- OpenAI API Key (for AI assistant features)
- Webcam (for face recognition testing)

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/attendance-system.git
cd attendance-system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root (copy from `.env.example`):
```bash
cp .env.example .env
```

Then edit the `.env` file with your actual values:
```env
SECRET_KEY=your-django-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3  # Or PostgreSQL URL
OPENAI_API_KEY=your-openai-api-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
```

**⚠️ Security Note:** Never commit your `.env` file to version control. It's already included in `.gitignore`.

### 5. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Create Media Directories
```bash
mkdir -p students  # For student images
mkdir -p media    # For uploaded files
```

### 7. Run Development Server
```bash
python manage.py runserver
```

Visit `http://localhost:8000` in your browser.

## 📖 Usage Guide

### For Teachers
1. **Sign Up/Login**: Create account or login with existing credentials
2. **Create Classes**: Set up classes and assign students
3. **Schedule Sessions**: Create attendance sessions with date/time
4. **Take Attendance**: Use webcam for real-time face recognition
5. **View Analytics**: Access dashboard for insights and predictions
6. **AI Assistant**: Ask natural language questions about attendance data

### For Administrators
- Full system access including user management
- Cross-teacher analytics and reporting
- System configuration and maintenance

### Key Endpoints
- `/` - Home page with attendance taking
- `/dashboard/` - Main analytics dashboard
- `/advanced_analytics/` - ML-powered insights
- `/ai_assistant/` - Natural language queries
- `/class_management/` - Teacher class management
- `/admin/` - Django admin interface

## 🔧 API Documentation

### Core Endpoints

#### Attendance Management
```
POST /take_attendance/
- Real-time face recognition and logging

POST /take_attendance_with_session/
- Session-based attendance with validation

GET /get_sessions/
- Retrieve teacher's upcoming sessions
```

#### Analytics & Data
```
GET /dashboard_data/
- Comprehensive attendance analytics

GET /advanced_analytics_data/
- ML-enhanced analytics with predictions

POST /ai_assistant/
- Natural language query processing
```

#### User Management
```
POST /signup/ - User registration
POST /login/ - User authentication
POST /create_class/ - Class creation
POST /assign_student_to_class/ - Student assignment
```

## 🤖 AI/ML Features Deep Dive

### Predictive Modeling
- **Algorithm**: Linear regression with TensorFlow.js
- **Features**: Day of week, recent attendance, historical patterns
- **Output**: 7-day attendance forecast with confidence intervals

### Risk Assessment
- **Methodology**: Multi-factor analysis including attendance rate, lateness patterns
- **Classification**: High/Medium/Low risk categories
- **Intervention**: Automated recommendations for at-risk students

### Pattern Recognition
- **Technique**: K-means clustering for behavior segmentation
- **Visualization**: Scatter plots showing attendance vs. consistency
- **Insights**: Identification of attendance behavior patterns

## 🧪 Testing

### Running Tests
```bash
python manage.py test
```

### Manual Testing Checklist
- [ ] Face recognition accuracy across lighting conditions
- [ ] Attendance logging without duplicates
- [ ] AI assistant response accuracy
- [ ] Chart rendering and data accuracy
- [ ] User permission enforcement
- [ ] Mobile responsiveness

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run with Docker
docker build -t attendance-system .
docker run -p 8000:8000 attendance-system
```

### Production Considerations
- Use PostgreSQL for database
- Configure static file serving (nginx/Apache)
- Set up SSL certificates
- Implement proper logging and monitoring
- Configure backup strategies

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure cross-browser compatibility

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenCV and face_recognition communities for computer vision tools
- TensorFlow.js team for browser-based ML capabilities
- OpenAI for powerful NLP integration
- Django community for the excellent web framework

## 📞 Contact

**Developer**: [Your Name]
- **Email**: your.email@example.com
- **LinkedIn**: [Your LinkedIn Profile]
- **GitHub**: [Your GitHub Profile]
- **Portfolio**: [Your Portfolio Website]

---

**Note**: This project demonstrates advanced full-stack development skills, AI/ML integration, computer vision expertise, and production-ready software engineering practices. Perfect for showcasing in technical interviews and job applications.
