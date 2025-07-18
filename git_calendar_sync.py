import subprocess
import os
import shutil
from datetime import datetime

def update_calendar_and_push():
    """
    Updates the ICS calendar file and pushes changes to servidorCalendario repository only
    """
    try:
        # Import the csv_to_ics function
        from convert_csv_to_ics import csv_to_ics
        
        # Generate updated ICS file
        print("🔄 Updating calendar.ics...")
        csv_to_ics()
        
        # Copy the calendar.ics to servidorCalendario folder
        servidor_calendar_path = "servidorCalendario/calendar.ics"
        if os.path.exists("github-pages-setup/calendar.ics"):
            shutil.copy2("github-pages-setup/calendar.ics", servidor_calendar_path)
            print("✅ Copied calendar.ics to servidorCalendario folder")
        
        # Push only to servidorCalendario repository
        return push_to_servidor_repository()
        
    except Exception as e:
        print(f"❌ Error updating calendar: {e}")
        return False

def push_to_servidor_repository():
    """
    Push changes to the servidorCalendario repository
    """
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
        commit_message = f"Auto-update calendar: {timestamp}"
        
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

def git_setup_check():
    """
    Check if servidorCalendario repository is properly configured
    """
    try:
        print("🔍 Checking servidorCalendario repository...")
        
        servidor_path = "servidorCalendario"
        
        # Check if directory exists
        if not os.path.exists(servidor_path):
            print("❌ servidorCalendario directory not found")
            return False
            
        # Check if git is initialized
        result = subprocess.run(['git', 'status'], 
                              capture_output=True, 
                              text=True, 
                              cwd=servidor_path)
        
        if result.returncode != 0:
            print("🔧 ServidorCalendario Git Setup Required:")
            print("1. cd servidorCalendario")
            print("2. git init")
            print("3. git remote add origin https://github.com/yourusername/calendario-servidor.git")
            print("4. git branch -M main")
            print("5. git push -u origin main")
            return False
            
        # Check if remote origin exists
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                              capture_output=True, 
                              text=True, 
                              cwd=servidor_path)
        
        if result.returncode != 0:
            print("🔧 ServidorCalendario Git Remote Required:")
            print("cd servidorCalendario")
            print("git remote add origin https://github.com/yourusername/calendario-servidor.git")
            return False
            
        print(f"✅ ServidorCalendario repository configured with remote: {result.stdout.strip()}")
        return True
        
    except Exception as e:
        print(f"❌ Error checking servidorCalendario repository: {e}")
        return False

if __name__ == "__main__":
    if git_setup_check():
        update_calendar_and_push()
    else:
        print("Please set up git first using the commands above.")
