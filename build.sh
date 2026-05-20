#!/bin/bash
set -e

echo "🚀 Starting deployment build..."

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

# Collect static files (non-fatal)
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear || echo "⚠️  collectstatic failed, continuing..."

echo "✅ Build completed successfully!"