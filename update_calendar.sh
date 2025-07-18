#!/bin/bash
# Simple script to update calendar manually

echo "🔄 Manual Calendar Update"
echo "========================"

# Check if we're in the right directory
if [ ! -f "reservations.csv" ]; then
    echo "❌ Error: reservations.csv not found!"
    echo "Please make sure you're running this script from the project root directory."
    exit 1
fi

# Run the Python script
python3 update_calendar.py

echo "✅ Calendar update script completed!"
