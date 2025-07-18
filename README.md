# Cabaña Reservation System 🏡

A complete reservation management system with automatic calendar sync to GitHub Pages.

## Features

- 📅 **Reservation Management**: Create, modify, and delete reservations
- 🤖 **Telegram Bot**: Chat interface with voice message support
- 📱 **AI Integration**: Gemini AI for natural language processing
- 📊 **Calendar Export**: Automatic ICS calendar generation
- 🔄 **Auto-Sync**: Automatic GitHub Pages updates
- 🌐 **Web Interface**: Simple web interface for calendar access

## Quick Start

### 1. Initial Setup

```bash
# Run the setup script
./setup_git_sync.sh
```

### 2. GitHub Repository Setup

1. Create a new repository on GitHub
2. Copy the repository URL
3. Run these commands:

```bash
git remote add origin https://github.com/yourusername/your-repo.git
git branch -M main
git push -u origin main
```

### 3. Enable GitHub Pages

1. Go to your repository settings
2. Navigate to "Pages" section
3. Set source to "Deploy from a branch"
4. Select branch: `main`
5. Select folder: `/github-pages-setup`

Your calendar will be available at: `https://yourusername.github.io/your-repo/calendar.ics`

## Usage

### Automatic Calendar Updates

The system automatically updates the calendar and pushes to GitHub whenever you:

- **Make a reservation**: `make_reservation(guest_name, check_in_date, total_nights, cabin, ...)`
- **Delete a reservation**: `delete_reservation(guest_name)`
- **Modify a reservation**: `modify_reservation(guest_name, ...)`

### Manual Calendar Update

If you need to manually update the calendar:

```bash
python update_calendar_manually.py
```

### Using the Calendar

Once deployed, users can:

1. **Subscribe to calendar**: Add `https://yourusername.github.io/your-repo/calendar.ics` to their calendar app
2. **Download calendar**: Visit the GitHub Pages URL to download the ICS file
3. **View online**: Visit `https://yourusername.github.io/your-repo/` for a simple web interface

## File Structure

```
├── main.py                     # Core reservation system
├── telegram_bot.py             # Telegram bot integration
├── app.py                      # Flask web interface
├── convert_csv_to_ics.py       # Calendar conversion utility
├── git_calendar_sync.py        # Auto-sync functionality
├── setup_git_sync.sh           # Setup script
├── update_calendar_manually.py # Manual update script
├── reservations.csv            # Reservation data
├── static/
│   ├── reservations.ics        # Calendar for web app
│   └── style.css              # Web app styles
├── github-pages-setup/
│   ├── index.html             # GitHub Pages landing page
│   └── calendar.ics           # Public calendar file
└── templates/
    └── index.html             # Flask templates
```

## Environment Variables

Create a `.env` file with:

```
GEMINI_API_KEY=your_gemini_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

## Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

## Troubleshooting

### Git Issues

If auto-sync fails:

1. Check git status: `git status`
2. Verify remote: `git remote -v`
3. Test manual push: `git push`

### Calendar Not Updating

1. Check GitHub Pages is enabled
2. Verify the calendar.ics file exists in github-pages-setup/
3. Try manual update: `python update_calendar_manually.py`

### Telegram Bot Issues

1. Verify bot token in `.env`
2. Check bot is running: `python telegram_bot.py`
3. Test with ngrok for local development

## Support

For issues or questions:
1. Check the console output for error messages
2. Verify all environment variables are set
3. Ensure git is properly configured
4. Check GitHub Pages deployment status

---

🎉 **Enjoy your automated reservation system!**
