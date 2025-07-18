#!/usr/bin/env python3
"""
Manual Calendar ICS Update Script
This script manually updates the calendar.ics file from the reservations.csv data.
"""

import pandas as pd
from datetime import datetime, timedelta
import os
import shutil
import subprocess
import sys


def csv_to_ics():
    """Convert CSV reservations to ICS calendar format"""
    
    # Read the CSV file
    try:
        df = pd.read_csv('reservations.csv', parse_dates=['check_in_dates', 'check_out_dates'])
        print(f"✅ Found {len(df)} reservations in CSV file")
    except FileNotFoundError:
        print("❌ Error: reservations.csv file not found!")
        return None
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return None
    
    if df.empty:
        print("⚠️  No reservations found in CSV file")
        return ""
    
    # ICS file header
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Cabaña Reservations//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    # Add each reservation as an event
    for _, reservation in df.iterrows():
        # Format dates for ICS (YYYYMMDD format)
        check_in = reservation['check_in_dates'].strftime('%Y%m%d')
        check_out = reservation['check_out_dates'].strftime('%Y%m%d')
        
        # Create a unique ID for the event
        guest_name_clean = reservation['guest_names'].replace(' ', '-').replace(',', '')
        uid = f"reservation-{guest_name_clean}-{check_in}@cabana.com"
        
        # Create event summary
        summary = f"Reserva: {reservation['guest_names']} - {reservation['cabin']}"
        
        # Create description with all details
        description_parts = [
            f"Huésped: {reservation['guest_names']}",
            f"Cabaña: {reservation['cabin']}",
            f"Noches: {reservation['total_nights']}",
            f"Total: ${reservation['reservation_total']}",
            f"Pagado: ${reservation['reservation_payed']}"
        ]
        
        # Add phone number if available
        if pd.notna(reservation['cellphone_numbers']) and str(reservation['cellphone_numbers']).strip():
            description_parts.append(f"Teléfono: {reservation['cellphone_numbers']}")
        
        # Add notes if available
        if pd.notna(reservation['notes']) and str(reservation['notes']).strip():
            description_parts.append(f"Notas: {reservation['notes']}")
        
        description = "\\n".join(description_parts)
        
        # Add event to ICS content
        ics_content.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART;VALUE=DATE:{check_in}",
            f"DTEND;VALUE=DATE:{check_out}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            f"LOCATION:{reservation['cabin']} - Cabaña",
            f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT"
        ])
        
        print(f"  📅 Added: {reservation['guest_names']} ({reservation['cabin']}) - {check_in} to {check_out}")
    
    # ICS file footer
    ics_content.append("END:VCALENDAR")
    
    return '\n'.join(ics_content)


def create_directories():
    """Create necessary directories if they don't exist"""
    directories = ["static", "github-pages-setup", "servidorCalendario"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"📁 Created directory: {directory}")


def save_ics_files(ics_content):
    """Save ICS content to all required locations"""
    if not ics_content:
        print("❌ No ICS content to save")
        return False
    
    # Create directories if they don't exist
    create_directories()
    
    # Define file paths
    files_to_update = [
        "static/reservations.ics",
        "github-pages-setup/calendar.ics",
        "servidorCalendario/calendar.ics"
    ]
    
    success_count = 0
    
    for file_path in files_to_update:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(ics_content)
            print(f"✅ Updated {file_path}")
            success_count += 1
        except Exception as e:
            print(f"❌ Error updating {file_path}: {e}")
    
    # Ensure HTML files are present (copy from github-pages-setup to servidorCalendario)
    try:
        github_html = "github-pages-setup/index.html"
        servidor_html = "servidorCalendario/index.html"
        
        if os.path.exists(github_html) and os.path.exists(servidor_html):
            print("✅ HTML files are already up to date")
        elif os.path.exists(github_html):
            shutil.copy2(github_html, servidor_html)
            print("✅ Copied HTML file to servidorCalendario")
    except Exception as e:
        print(f"⚠️  Note: Could not sync HTML files: {e}")
    
    return success_count == len(files_to_update)


def push_to_servidor_repository():
    """Push changes to the servidorCalendario repository"""
    try:
        print("\n📁 Pushing to servidorCalendario repository...")
        
        servidor_path = "servidorCalendario"
        
        # Check if servidorCalendario directory exists
        if not os.path.exists(servidor_path):
            print("❌ servidorCalendario directory not found")
            return False
            
        # Check if it's a git repository
        result = subprocess.run(['git', 'status'], 
                              capture_output=True, 
                              text=True, 
                              cwd=servidor_path)
        
        if result.returncode != 0:
            print("❌ servidorCalendario is not a git repository")
            return False
            
        # Add the updated calendar.ics file
        subprocess.run(['git', 'add', 'calendar.ics'], cwd=servidor_path)
        print("✅ Added calendar.ics to servidorCalendario git")
        
        # Create commit message with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Manual calendar update: {timestamp}"
        
        # Commit the changes
        result = subprocess.run(['git', 'commit', '-m', commit_message], 
                              capture_output=True, 
                              text=True, 
                              cwd=servidor_path)
        
        if result.returncode == 0:
            print(f"✅ Committed changes to servidorCalendario: {commit_message}")
            
            # Push to GitHub
            push_result = subprocess.run(['git', 'push'], 
                                       capture_output=True, 
                                       text=True, 
                                       cwd=servidor_path)
            
            if push_result.returncode == 0:
                print("🚀 Successfully pushed to servidorCalendario repository!")
                return True
            else:
                print(f"❌ Failed to push to servidorCalendario repository: {push_result.stderr}")
                return False
        else:
            if "nothing to commit" in result.stdout:
                print("ℹ️  No changes to commit in servidorCalendario repository")
                return True
            else:
                print(f"❌ Failed to commit to servidorCalendario repository: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"❌ Error pushing to servidorCalendario repository: {e}")
        return False


def update_calendar(push_to_git=True):
    """Main function to update calendar"""
    print("🔄 Manual Calendar Update Script")
    print("=" * 40)
    
    # Convert CSV to ICS
    print("\n📊 Converting CSV to ICS format...")
    ics_content = csv_to_ics()
    
    if ics_content is None:
        print("❌ Failed to generate ICS content")
        return False
    
    # Save ICS files
    print("\n💾 Saving ICS files...")
    if not save_ics_files(ics_content):
        print("❌ Failed to save some ICS files")
        return False
    
    # Push to git repository if requested
    if push_to_git:
        print("\n🔄 Pushing to git repository...")
        if not push_to_servidor_repository():
            print("❌ Failed to push to git repository")
            return False
    
    print("\n🎉 Calendar update completed successfully!")
    return True


def main():
    """Main entry point"""
    print("Manual Calendar ICS Update Script")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('reservations.csv'):
        print("❌ Error: reservations.csv not found!")
        print("Please make sure you're running this script from the project root directory.")
        sys.exit(1)
    
    # Parse command line arguments
    push_to_git = True
    if len(sys.argv) > 1 and sys.argv[1] == '--no-push':
        push_to_git = False
        print("⚠️  Git push disabled (--no-push flag)")
    
    # Update calendar
    success = update_calendar(push_to_git)
    
    if success:
        print("\n✅ All operations completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some operations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
