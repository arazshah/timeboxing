#!/bin/bash

echo "🚀 Deploying Personal Timebox Application..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Environment setup
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment file..."
    cat > .env << EOL
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
DB_NAME=personal_timebox
DB_USER=postgres
DB_PASSWORD=change-this-password
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
REDIS_URL=redis://127.0.0.1:6379/0
EOL
    echo "✏️ Please edit .env file with your actual settings"
fi

# Database setup
echo "🗄️ Setting up database..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if needed
echo "👤 Creating superuser..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️ Superuser already exists')
EOF

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create sample data (optional)
read -p "🎯 Create sample data for testing? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py create_sample_data --username demo
    echo "✅ Sample data created for user 'demo' with password 'testpass123'"
fi

echo "🎉 Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Edit .env file with your actual settings"
echo "   2. Set up PostgreSQL database"
echo "   3. Configure email settings for password reset"
echo "   4. Set up Redis for caching (optional)"
echo ""
echo "🌐 Development server: python manage.py runserver"
echo "🔧 Admin panel: http://localhost:8000/admin/ (admin/admin123)"
echo "📊 Dashboard: http://localhost:8000/"
echo ""
echo "💡 Don't forget to activate your virtual environment: source venv/bin/activate"