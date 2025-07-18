#!/bin/bash

# Setup script for automated calendar sync to GitHub
echo "🚀 Setting up automated calendar sync to GitHub..."

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install git first."
    exit 1
fi

# Check if we're already in a git repository
if [ -d ".git" ]; then
    echo "✅ Git repository already exists."
else
    echo "🔧 Initializing git repository..."
    git init
    echo "✅ Git repository initialized."
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/

# Environment variables
.env
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
EOF
    echo "✅ .gitignore created."
fi

# Stage all files
echo "📁 Adding files to git..."
git add .
git commit -m "Initial commit: Cabaña reservation system with auto-sync"

# Check if remote origin exists
if git remote get-url origin &> /dev/null; then
    echo "✅ Remote origin already configured."
    REMOTE_URL=$(git remote get-url origin)
    echo "   Remote URL: $REMOTE_URL"
else
    echo ""
    echo "🔗 GitHub Repository Setup Required:"
    echo "1. Go to https://github.com and create a new repository"
    echo "2. Copy the repository URL (e.g., https://github.com/yourusername/botCabana.git)"
    echo "3. Run the following commands:"
    echo ""
    echo "   git remote add origin https://github.com/yourusername/your-repo.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    echo "4. For GitHub Pages, go to your repository settings and enable GitHub Pages"
    echo "   - Source: Deploy from a branch"
    echo "   - Branch: main"
    echo "   - Folder: /github-pages-setup"
    echo ""
    echo "After setup, your calendar will be available at:"
    echo "https://yourusername.github.io/your-repo/calendar.ics"
    echo ""
fi

echo "🎉 Setup complete!"
echo ""
echo "Now whenever you:"
echo "• Make a new reservation"
echo "• Delete a reservation"
echo "• Modify a reservation"
echo ""
echo "The calendar.ics file will be automatically updated and pushed to GitHub!"
