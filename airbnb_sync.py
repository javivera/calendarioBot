#!/usr/bin/env python3
"""
Airbnb Calendar Sync Script
Fetches calendar data from Airbnb and syncs it with the local reservations.csv file.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import logging
from icalendar import Calendar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AirbnbCalendarSync:
    def __init__(self, airbnb_url, csv_file='reservations.csv'):
        self.airbnb_url = airbnb_url
        self.csv_file = csv_file
        self.airbnb_guest_name = "Airbnb Guest"
        self.airbnb_cabin = "Airbnb Booking"
        
    def fetch_airbnb_calendar(self):
        """Fetch the Airbnb calendar from the URL"""
        try:
            logger.info(f"Fetching Airbnb calendar from: {self.airbnb_url}")
            response = requests.get(self.airbnb_url, timeout=30)
            response.raise_for_status()
            
            logger.info("✅ Successfully fetched Airbnb calendar")
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"❌ Error fetching Airbnb calendar: {e}")
            return None
    
    def parse_airbnb_calendar(self, ical_data):
        """Parse the iCal data from Airbnb"""
        try:
            calendar = Calendar.from_ical(ical_data)
            blocked_dates = []
            
            for component in calendar.walk():
                if component.name == "VEVENT":
                    # Get start and end dates
                    start_date = component.get('dtstart').dt
                    end_date = component.get('dtend').dt
                    summary = str(component.get('summary', 'Airbnb Booking'))
                    
                    # Convert to datetime if it's a date
                    if hasattr(start_date, 'date'):
                        start_date = start_date.date()
                    if hasattr(end_date, 'date'):
                        end_date = end_date.date()
                    
                    # Convert to datetime objects for consistency
                    if not isinstance(start_date, datetime):
                        start_date = datetime.combine(start_date, datetime.min.time())
                    if not isinstance(end_date, datetime):
                        end_date = datetime.combine(end_date, datetime.min.time())
                    
                    blocked_dates.append({
                        'start': start_date,
                        'end': end_date,
                        'summary': summary
                    })
            
            logger.info(f"✅ Found {len(blocked_dates)} blocked periods in Airbnb calendar")
            return blocked_dates
            
        except Exception as e:
            logger.error(f"❌ Error parsing Airbnb calendar: {e}")
            return []
    
    def load_reservations(self):
        """Load existing reservations from CSV"""
        try:
            if not os.path.exists(self.csv_file):
                logger.warning(f"⚠️  CSV file {self.csv_file} not found, creating new one")
                return pd.DataFrame(columns=[
                    'guest_names', 'check_in_dates', 'check_out_dates', 
                    'cellphone_numbers', 'total_nights', 'reservation_total',
                    'reservation_payed', 'notes', 'cabin'
                ])
            
            df = pd.read_csv(self.csv_file)
            df['check_in_dates'] = pd.to_datetime(df['check_in_dates'])
            df['check_out_dates'] = pd.to_datetime(df['check_out_dates'])
            
            logger.info(f"✅ Loaded {len(df)} existing reservations")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error loading reservations: {e}")
            return pd.DataFrame(columns=[
                'guest_names', 'check_in_dates', 'check_out_dates', 
                'cellphone_numbers', 'total_nights', 'reservation_total',
                'reservation_payed', 'notes', 'cabin'
            ])
    
    def is_airbnb_reservation(self, guest_name, notes):
        """Check if a reservation is from Airbnb sync"""
        return (guest_name == self.airbnb_guest_name or 
                (notes and 'Airbnb' in str(notes)))
    
    def remove_old_airbnb_reservations(self, df):
        """Remove old Airbnb reservations to avoid duplicates"""
        # Keep only non-Airbnb reservations
        mask = ~df.apply(lambda row: self.is_airbnb_reservation(
            row['guest_names'], row['notes']), axis=1)
        
        old_count = len(df)
        df_filtered = df[mask].copy()
        removed_count = old_count - len(df_filtered)
        
        if removed_count > 0:
            logger.info(f"🧹 Removed {removed_count} old Airbnb reservations")
        
        return df_filtered
    
    def add_airbnb_reservations(self, df, blocked_dates):
        """Add new Airbnb reservations to the dataframe, skipping those without a guest name."""
        new_reservations = []
        skipped_count = 0
        skipped_no_guest = 0

        for booking in blocked_dates:
            start_date = booking['start']
            end_date = booking['end']
            summary = booking.get('summary', '').strip()

            # Skip if no guest name in summary
            if not summary or summary.lower() in ['airbnb booking', '']:
                logger.info(f"⏩ Skipping Airbnb reservation with missing guest name: {start_date.date()} to {end_date.date()}")
                skipped_no_guest += 1
                continue

            # Calculate nights
            nights = (end_date - start_date).days

            # Skip if less than 2 nights (1 night reservations are ignored)
            if nights < 2:
                logger.info(f"⏩ Skipping short Airbnb reservation ({nights} night{'s' if nights != 1 else ''}): {start_date.date()} to {end_date.date()}")
                skipped_count += 1
                continue

            # Skip if reservation is longer than 31 nights
            if nights > 31:
                logger.info(f"⏩ Skipping long Airbnb reservation ({nights} nights): {start_date.date()} to {end_date.date()}")
                skipped_count += 1
                continue

            # Check if this reservation overlaps with any existing reservation
            overlapping_reservation = self.find_overlapping_reservation(df, start_date, end_date)
            if overlapping_reservation is not None:
                logger.info(f"⏩ Skipping Airbnb reservation due to overlap: {start_date.date()} to {end_date.date()}")
                skipped_count += 1
                continue

            logger.info(f"➕ Adding new Airbnb reservation: {start_date.date()} to {end_date.date()} for guest '{summary}'")

            # Create reservation entry
            reservation = {
                'guest_names': summary,
                'check_in_dates': start_date,
                'check_out_dates': end_date,
                'cellphone_numbers': '',
                'total_nights': nights,
                'reservation_total': 0,
                'reservation_payed': 0,
                'notes': f'Airbnb booking - {summary}',
                'cabin': self.airbnb_cabin
            }

            new_reservations.append(reservation)

        if new_reservations:
            new_df = pd.DataFrame(new_reservations)
            df = pd.concat([df, new_df], ignore_index=True)
            logger.info(f"➕ Added {len(new_reservations)} new Airbnb reservations")
        else:
            logger.info("ℹ️ No new Airbnb reservations to add")

        if skipped_count > 0:
            logger.info(f"⏩ Skipped {skipped_count} reservations (overlaps or too long)")
        if skipped_no_guest > 0:
            logger.info(f"⏩ Skipped {skipped_no_guest} reservations with missing guest name")

        return df
    
    def clean_cancelled_airbnb_reservations(self, df, blocked_dates):
        """Remove Airbnb reservations that are no longer in the Airbnb calendar"""
        if df.empty:
            return df
        
        # Get all current Airbnb blocked date ranges (date only, not datetime)
        current_airbnb_dates = set()
        for booking in blocked_dates:
            start_date = pd.to_datetime(booking['start']).date()
            end_date = pd.to_datetime(booking['end']).date()
            current_airbnb_dates.add((start_date, end_date))
        
        # Find Airbnb reservations that are no longer in the calendar
        airbnb_reservations = df[df.apply(lambda row: self.is_airbnb_reservation(
            row['guest_names'], row['notes']), axis=1)]
        
        reservations_to_remove = []
        for idx, reservation in airbnb_reservations.iterrows():
            check_in = pd.to_datetime(reservation['check_in_dates']).date()
            check_out = pd.to_datetime(reservation['check_out_dates']).date()
            
            # If this reservation is not in the current Airbnb calendar, mark for removal
            if (check_in, check_out) not in current_airbnb_dates:
                reservations_to_remove.append(idx)
        
        if reservations_to_remove:
            df = df.drop(reservations_to_remove)
            logger.info(f"🧹 Removed {len(reservations_to_remove)} cancelled Airbnb reservations")
        
        return df
    
    def find_overlapping_reservation(self, df, start_date, end_date):
        """Check if a reservation overlaps with any existing reservation"""
        if df.empty:
            return None
        
        # Convert dates to date objects for comparison (ignore time)
        start_date = pd.to_datetime(start_date).date()
        end_date = pd.to_datetime(end_date).date()
        
        # Check for any overlapping reservations
        for idx, row in df.iterrows():
            existing_start = pd.to_datetime(row['check_in_dates']).date()
            existing_end = pd.to_datetime(row['check_out_dates']).date()
            
            # Check if dates overlap
            # Two date ranges overlap if: start1 < end2 AND start2 < end1
            if start_date < existing_end and existing_start < end_date:
                logger.info(f"🚫 Overlap detected with {row['guest_names']}: {existing_start} to {existing_end}")
                return row
        
        return None
    
    def save_reservations(self, df):
        """Save the updated reservations to CSV"""
        try:
            # Sort by check-in date
            df = df.sort_values('check_in_dates')
            
            # Save to CSV
            df.to_csv(self.csv_file, index=False)
            logger.info(f"✅ Saved {len(df)} reservations to {self.csv_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving reservations: {e}")
    
    def sync_calendar(self):
        """Main sync function"""
        logger.info("🔄 Starting Airbnb calendar sync")
        
        # Fetch Airbnb calendar
        ical_data = self.fetch_airbnb_calendar()
        if not ical_data:
            logger.error("❌ Failed to fetch Airbnb calendar")
            return False
        
        # Parse blocked dates
        blocked_dates = self.parse_airbnb_calendar(ical_data)
        if not blocked_dates:
            logger.info("ℹ️  No blocked dates found in Airbnb calendar")
            return True
        
        # Load existing reservations
        df = self.load_reservations()
        
        # Remove Airbnb reservations that are no longer in the Airbnb calendar
        df = self.clean_cancelled_airbnb_reservations(df, blocked_dates)
        
        # Add new Airbnb reservations (duplicates are automatically checked)
        df = self.add_airbnb_reservations(df, blocked_dates)
        
        # Save updated reservations
        self.save_reservations(df)
        
        logger.info("🎉 Airbnb calendar sync completed successfully")
        return True

def run_continuous_sync():
    """Run the sync continuously every hour"""
    airbnb_url = "https://www.airbnb.com/calendar/ical/36870432.ics?s=52f050865b49d6a3f095e1f8bcb2fb0a"
    sync = AirbnbCalendarSync(airbnb_url)
    
    logger.info("🚀 Starting continuous Airbnb calendar sync (every hour)")
    
    while True:
        try:
            sync.sync_calendar()
            logger.info("⏰ Waiting 1 hour until next sync...")
            time.sleep(3600)  # Wait 1 hour
        except KeyboardInterrupt:
            logger.info("🛑 Sync stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            logger.info("⏰ Waiting 1 hour before retry...")
            time.sleep(3600)

def run_single_sync():
    """Run sync once"""
    airbnb_url = "https://www.airbnb.com/calendar/ical/36870432.ics?s=52f050865b49d6a3f095e1f8bcb2fb0a"
    sync = AirbnbCalendarSync(airbnb_url)
    return sync.sync_calendar()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        print("Running single sync...")
        run_single_sync()
    else:
        print("Running continuous sync (every hour)...")
        print("Use --once flag to run just once")
        print("Press Ctrl+C to stop")
        run_continuous_sync()
