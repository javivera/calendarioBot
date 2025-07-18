#!/usr/bin/env python3
"""
Manual calendar update script
Run this if you want to manually update the calendar and push to GitHub
"""

from git_calendar_sync import update_calendar_and_push, git_setup_check

def main():
    print("🔄 Manual Calendar Update")
    print("=" * 40)
    
    # Check git setup
    if not git_setup_check():
        print("\n❌ Git setup incomplete. Please run setup_git_sync.sh first.")
        return
    
    # Update calendar and push
    print("\n🔄 Updating calendar...")
    success = update_calendar_and_push()
    
    if success:
        print("\n✅ Calendar successfully updated and pushed to GitHub!")
        print("🌐 Your calendar should now be available at:")
        print("   https://yourusername.github.io/your-repo/calendar.ics")
    else:
        print("\n❌ Calendar update failed. Check the errors above.")

if __name__ == "__main__":
    main()
