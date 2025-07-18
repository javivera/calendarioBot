# Enhanced Calendar Webpage

The GitHub Pages website now displays an interactive calendar showing occupied days from your reservations!

## 🌟 New Features

### Visual Calendar
- **Interactive Calendar**: Shows current month and next month side by side
- **Color-coded Days**: 
  - 🟢 Gray: Available days
  - 🔴 Red: Occupied days (with pulsing animation)
  - 🟡 Orange: Today's date
- **Responsive Design**: Works on both desktop and mobile devices

### Reservation Display
- **Reservation List**: Shows all current reservations with details
- **Formatted Dates**: Easy to read date formats
- **Guest Information**: Complete reservation details including guest names, cabin, and notes

### Download Features
- **Direct Download**: Click to download the ICS file
- **Copy URL**: One-click copy of the calendar URL for adding to calendar apps
- **Calendar Integration**: Works with Google Calendar, Outlook, Apple Calendar, etc.

## 🎨 Design Features

- **Modern UI**: Beautiful gradient background and clean card-based layout
- **Smooth Animations**: Hover effects and transitions
- **Mobile-Friendly**: Responsive design that works on all screen sizes
- **Professional Look**: Modern styling with proper spacing and typography

## 📂 Files Updated

1. **`github-pages-setup/index.html`** - New enhanced webpage for GitHub Pages
2. **`servidorCalendario/index.html`** - Updated to match the new design
3. **`update_calendar.py`** - Updated to maintain both HTML files

## 🔧 How It Works

1. **JavaScript fetches the calendar.ics file** from the same directory
2. **Parses ICS data** to extract reservation dates and details
3. **Generates interactive calendars** for current and next month
4. **Highlights occupied dates** in red with animation
5. **Displays reservation details** in a clean list format

## 🚀 Deployment

When you push your changes to GitHub:
1. The `servidorCalendario` repository will have the updated HTML and ICS files
2. GitHub Pages will automatically serve the new enhanced calendar
3. Visitors can see:
   - Interactive calendar with occupied dates
   - Complete reservation details
   - Easy download options
   - Professional, mobile-friendly design

## 📱 Usage

### For Website Visitors:
- **View Calendar**: See which dates are occupied at a glance
- **Check Reservations**: Browse current reservations with full details
- **Download Calendar**: Add to their own calendar apps
- **Copy URL**: Share the calendar URL with others

### For You:
- **Update Reservations**: Just update `reservations.csv` and run the update script
- **Automatic Sync**: The webpage automatically reflects changes
- **No Manual HTML Editing**: Everything updates automatically

## 🔄 Updating Process

1. **Edit `reservations.csv`** with new/updated reservations
2. **Run update script**: `python3 update_calendar.py`
3. **Calendar Updates**: Both ICS files and HTML files stay in sync
4. **Push to GitHub**: Changes appear on the live website

## 🎯 Benefits

- **Professional Appearance**: Much more appealing than a simple download link
- **User-Friendly**: Easy to see availability at a glance
- **Mobile-Optimized**: Works perfectly on phones and tablets
- **Automatic Updates**: No manual webpage maintenance required
- **Calendar Integration**: Still provides easy calendar subscription

The enhanced calendar webpage transforms your simple file server into a professional-looking reservation calendar that's both functional and beautiful!
