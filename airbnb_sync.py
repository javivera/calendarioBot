#!/usr/bin/env python3
"""
Airbnb Calendar Sync Script
Fetches calendar data from Airbnb and syncs it with the local reservations.csv file.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import calendar
import time
import os
import shutil
import logging
import subprocess
from icalendar import Calendar
import unicodedata


def normalize_text(s):
    """Normalize text by removing accents, trimming, and lowercasing."""
    if s is None:
        return ''
    s = str(s)
    nkfd = unicodedata.normalize('NFKD', s)
    without_accents = ''.join([c for c in nkfd if not unicodedata.combining(c)])
    return without_accents.encode('ascii', 'ignore').decode('ascii').strip().lower()

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
    def __init__(self, airbnb_urls, csv_file='reservations.csv'):
        """airbnb_urls may be a single URL string or a list of dicts {'url':..., 'cabin':...}
        """
        self.csv_file = csv_file
        self.airbnb_guest_name = "Airbnb Guest"
        self.airbnb_cabin = "Airbnb Booking"

        # Patterns (normalized) considered as missing/placeholder guest names or notes
        self._airbnb_placeholder_summaries = set([
            normalize_text('Airbnb Booking'),
            normalize_text('Airbnb (Not available)'),
            normalize_text('airbnb (not available)'),
            normalize_text('airbnb guest'),
            normalize_text('airbnb')
        ])

        # Normalize incoming sources into a list of dicts with 'url' and 'cabin'
        if isinstance(airbnb_urls, str):
            self.airbnb_sources = [{'url': airbnb_urls, 'cabin': self.airbnb_cabin}]
        elif isinstance(airbnb_urls, list):
            normalized = []
            for item in airbnb_urls:
                if isinstance(item, str):
                    normalized.append({'url': item, 'cabin': self.airbnb_cabin})
                elif isinstance(item, dict) and 'url' in item:
                    cabin = item.get('cabin', self.airbnb_cabin)
                    normalized.append({'url': item['url'], 'cabin': cabin})
            self.airbnb_sources = normalized
        else:
            raise ValueError('airbnb_urls must be a string or a list')
        
    def fetch_airbnb_calendar(self, url):
        """Fetch the Airbnb calendar from the provided URL"""
        try:
            logger.info(f"Fetching Airbnb calendar from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            logger.info("✅ Successfully fetched Airbnb calendar")
            return response.text

        except requests.RequestException as e:
            logger.error(f"❌ Error fetching Airbnb calendar ({url}): {e}")
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
        """Add new Airbnb reservations to the dataframe, skipping those without a guest name.

        Each booking in `blocked_dates` may include a 'cabin' key which will be used
        for the reservation's `cabin` column. If absent, `self.airbnb_cabin` is used.

        Returns a tuple `(df, conflicts)` where `conflicts` is a list of dicts with
        details for each non-touching overlap detected. `df` will include any safe
        additions (bookings that did not conflict).
        """
        new_reservations = []
        skipped_count = 0
        skipped_no_guest = 0
        conflicts = []

        # Helper to add months to a date without external deps (keeps same day when possible)
        def _add_months(d, months):
            """Return a date that's `months` after date `d`.

            Adjusts day downwards when the target month has fewer days.
            """
            if isinstance(d, datetime):
                d = d.date()
            year = d.year + (d.month - 1 + months) // 12
            month = (d.month - 1 + months) % 12 + 1
            day = min(d.day, calendar.monthrange(year, month)[1])
            return datetime(year, month, day).date()

        # Compute cutoff date: bookings starting strictly after this date will be ignored
        today_date = datetime.now().date()
        cutoff_date = _add_months(today_date, 7)

        for booking in blocked_dates:
            start_date = booking['start']
            end_date = booking['end']
            summary = booking.get('summary', '').strip()
            cabin_name = booking.get('cabin', self.airbnb_cabin)

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

            # Skip bookings that are too far in the future (more than 7 months ahead)
            try:
                booking_start_date = start_date.date() if hasattr(start_date, 'date') else pd.to_datetime(start_date).date()
            except Exception:
                booking_start_date = pd.to_datetime(start_date).date()

            if booking_start_date > cutoff_date:
                logger.info(f"⏩ Skipping distant Airbnb reservation (starts after {cutoff_date}): {booking_start_date} to {end_date.date()}")
                skipped_count += 1
                continue

            # Check if this reservation overlaps with any existing reservation for the same cabin
            overlapping_reservation = self.find_overlapping_reservation(df, start_date, end_date, cabin=cabin_name)
            if overlapping_reservation is not None:
                # A non-touching overlap was detected (find_overlapping_reservation returns a row for these)
                logger.info(f"🚫 Detected non-touching overlap with existing reservation ({overlapping_reservation.get('guest_names', '')}): {start_date.date()} to {end_date.date()} (cabin: {cabin_name})")
                skipped_count += 1
                conflicts.append({
                    'new_guest': summary,
                    'new_start': pd.to_datetime(start_date).date(),
                    'new_end': pd.to_datetime(end_date).date(),
                    'cabin': cabin_name,
                    'existing_guest': overlapping_reservation.get('guest_names', ''),
                    'existing_start': pd.to_datetime(overlapping_reservation['check_in_dates']).date(),
                    'existing_end': pd.to_datetime(overlapping_reservation['check_out_dates']).date()
                })
                # Do not add this booking; continue checking others so we can report all conflicts
                continue

            logger.info(f"➕ Adding new Airbnb reservation: {start_date.date()} to {end_date.date()} for guest '{summary}' (cabin: {cabin_name})")

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
                'cabin': cabin_name
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

        return df, conflicts
    
    def clean_cancelled_airbnb_reservations(self, df, blocked_dates):
        """Remove Airbnb reservations that are no longer in the Airbnb calendars.

        This function now considers the `cabin` when matching existing Airbnb reservations
        to the current blocked periods coming from the feeds.

        Important change: Do NOT remove past Airbnb reservations (their check_out < today),
        because Airbnb feeds often stop including past bookings once they are due.
        Only current/future Airbnb reservations are candidates for removal.
        """
        if df.empty:
            return df

        today = datetime.now().date()

        # Get all current Airbnb blocked date ranges including cabin
        current_airbnb_dates = set()
        for booking in blocked_dates:
            start_date = pd.to_datetime(booking['start']).date()
            end_date = pd.to_datetime(booking['end']).date()
            cabin = booking.get('cabin', self.airbnb_cabin)
            current_airbnb_dates.add((start_date, end_date, cabin))

        # Find Airbnb reservations that are no longer in the calendar
        airbnb_reservations = df[df.apply(lambda row: self.is_airbnb_reservation(
            row['guest_names'], row['notes']), axis=1)]

        reservations_to_remove = []
        for idx, reservation in airbnb_reservations.iterrows():
            check_in = pd.to_datetime(reservation['check_in_dates']).date()
            check_out = pd.to_datetime(reservation['check_out_dates']).date()
            cabin = reservation.get('cabin', self.airbnb_cabin)

            # Skip removing past reservations (preserve historical guests)
            if check_out < today:
                continue

            # If this reservation (with cabin) is not in the current Airbnb calendars, mark for removal
            if (check_in, check_out, cabin) not in current_airbnb_dates:
                reservations_to_remove.append(idx)

        if reservations_to_remove:
            df = df.drop(reservations_to_remove)
            logger.info(f"🧹 Removed {len(reservations_to_remove)} cancelled Airbnb reservations")

        return df
    
    def find_overlapping_reservation(self, df, start_date, end_date, cabin=None):
        """Check if a reservation overlaps with any existing reservation for the same cabin.

        Overlap rule modification:
        - Consider overlaps only within the same `cabin`.
        - Allow insertion only when the overlap is exactly where the new booking's start == existing end
          or new booking's end == existing start (i.e., touching at a single boundary). Otherwise treat as overlap.
        """
        if df.empty:
            return None

        # Normalize to date objects
        start_date = pd.to_datetime(start_date).date()
        end_date = pd.to_datetime(end_date).date()

        for idx, row in df.iterrows():
            # Only consider same-cabin rows (if cabin provided)
            if cabin is not None and str(row.get('cabin', '')).strip().lower() != str(cabin).strip().lower():
                continue

            existing_start = pd.to_datetime(row['check_in_dates']).date()
            existing_end = pd.to_datetime(row['check_out_dates']).date()

            # If the ranges are identical, count as overlap
            if start_date == existing_start and end_date == existing_end:
                logger.info(f"🚫 Exact overlap detected with {row['guest_names']}: {existing_start} to {existing_end}")
                return row

            # General overlap check
            if start_date < existing_end and existing_start < end_date:
                # Allow if they only touch at the boundary: new.start == existing.end or new.end == existing.start
                if start_date == existing_end or end_date == existing_start:
                    # touching boundary is acceptable (no overlap in occupancy)
                    logger.info(f"🔁 Touching boundary with {row['guest_names']}: {existing_start} to {existing_end}")
                    return None
                logger.info(f"🚫 Overlap detected with {row['guest_names']}: {existing_start} to {existing_end}")
                return row

        return None
    
    def backup_reservations(self):
        """Create a single daily timestamped backup of the reservations CSV in a 'backup' folder.

        This function will only create one backup per calendar day. It keeps a marker file
        named `.last_backup_date` inside the backup folder that contains the ISO date of the
        last backup. If the marker matches today's date, no new backup is created.
        """
        try:
            if not os.path.exists(self.csv_file):
                logger.info(f"ℹ️ No reservations file to backup: {self.csv_file}")
                return None

            csv_dir = os.path.dirname(os.path.abspath(self.csv_file))
            backup_dir = os.path.join(csv_dir, 'backup')
            os.makedirs(backup_dir, exist_ok=True)

            marker_path = os.path.join(backup_dir, '.last_backup_date')
            today_str = datetime.now().date().isoformat()

            # If marker exists and matches today, skip creating a new backup
            try:
                if os.path.exists(marker_path):
                    with open(marker_path, 'r', encoding='utf-8') as f:
                        last_date = f.read().strip()
                    if last_date == today_str:
                        logger.info(f"ℹ️ Backup already created today ({today_str}), skipping")
                        return None
            except Exception:
                # If reading marker fails, continue and attempt to create a backup
                logger.debug("⚠️ Could not read backup marker, proceeding to create backup")

            base = os.path.splitext(os.path.basename(self.csv_file))[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{base}_{timestamp}.csv"
            backup_path = os.path.join(backup_dir, backup_name)

            shutil.copy2(self.csv_file, backup_path)

            # Update marker file with today's date
            try:
                with open(marker_path, 'w', encoding='utf-8') as f:
                    f.write(today_str)
            except Exception:
                logger.warning("⚠️ Failed to write backup marker file")

            logger.info(f"💾 Backed up {self.csv_file} to {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"❌ Failed to backup reservations: {e}")
            return None

    def save_reservations(self, df):
        """Save the updated reservations to CSV and return success boolean."""
        try:
            # Sort by check-in date
            df = df.sort_values('check_in_dates')
            
            # Ensure price_per_night sits after total_nights if present
            if 'price_per_night' in df.columns and 'total_nights' in df.columns:
                cols = list(df.columns)
                while 'price_per_night' in cols:
                    cols.remove('price_per_night')
                insert_index = cols.index('total_nights') + 1
                cols.insert(insert_index, 'price_per_night')
                df = df[cols]
            
            # Save to CSV
            df.to_csv(self.csv_file, index=False)
            logger.info(f"✅ Saved {len(df)} reservations to {self.csv_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving reservations: {e}")
            return False

    def push_changes_to_repo(self, commit_message=None):
        """Git push disabled: this stub does not perform any git operations.

        Returns True to indicate no action was taken and to avoid triggering warnings
        in calling code.
        """
        logger.info("ℹ️ Git push disabled in airbnb_sync.py; skipping any git operations.")
        return True
    def sync_calendar(self):
        """Main sync function"""
        logger.info("🔄 Starting Airbnb calendar sync")
        # Backup current reservations file before making changes
        try:
            self.backup_reservations()
        except Exception:
            logger.exception("❌ Unexpected error while creating reservations backup")
        
        # Aggregate blocked dates from all configured Airbnb sources
        all_blocked = []
        for src in self.airbnb_sources:
            url = src['url']
            cabin = src.get('cabin', self.airbnb_cabin)
            ical_data = self.fetch_airbnb_calendar(url)
            if not ical_data:
                logger.warning(f"⚠️ Skipping source due to fetch failure: {url}")
                continue

            blocked = self.parse_airbnb_calendar(ical_data)
            # Tag each booking with the cabin source
            for b in blocked:
                b['cabin'] = cabin
            all_blocked.extend(blocked)

        if not all_blocked:
            logger.info("ℹ️  No blocked dates found in any Airbnb calendar source")
            return True

        # Load existing reservations
        df = self.load_reservations()

        # Remove Airbnb reservations that are no longer in the Airbnb calendars
        df = self.clean_cancelled_airbnb_reservations(df, all_blocked)

        # Add new Airbnb reservations (duplicates are automatically checked)
        df, conflicts = self.add_airbnb_reservations(df, all_blocked)

        # Save safe additions
        saved = self.save_reservations(df)

        # Always attempt to push saved changes to servidorCalendario repo (no env needed)
        if saved:
            pushed = self.push_changes_to_repo()
            if not pushed:
                logger.warning("⚠️ Reservations saved locally but failed to push to repository")

        # If conflicts were found, print short message and details for review
        if conflicts:
            logger.warning(f"⚠️ Found {len(conflicts)} conflicts while processing Airbnb calendars. Please review the logs for details.")
            print(f"⚠️ Airbnb sync detected {len(conflicts)} conflict(s). Details:")
            for c in conflicts:
                print(f" - Cabin: {c.get('cabin')} | New: {c.get('new_guest')} {c.get('new_start')} -> {c.get('new_end')} | Existing: {c.get('existing_guest')} {c.get('existing_start')} -> {c.get('existing_end')}")

        logger.info("🎉 Airbnb calendar sync completed successfully")

        # After saving reservations, regenerate ICS files by invoking update_calendar
        try:
            logger.info("🔄 Running update_calendar.py to regenerate ICS files")
            import update_calendar
            update_calendar.update_calendar(push_to_git=True)
        except Exception as e:
            logger.exception(f"❌ Failed to run update_calendar.py: {e}")

        return True

def run_continuous_sync():
    """Run the sync continuously every hour for multiple Airbnb sources"""
    sources = [
        {
            'url': 'https://www.airbnb.com/calendar/ical/36870432.ics?s=52f050865b49d6a3f095e1f8bcb2fb0a',
            'cabin': 'Colibri'
        },
        {
            'url': 'https://www.airbnb.com/calendar/ical/1520255215239969187.ics?s=827aa9a5237f3cc3f1a16bb8e72c6e33',
            'cabin': 'Peperina'
        }
    ]

    sync = AirbnbCalendarSync(sources)

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
    """Run sync once for multiple Airbnb sources"""
    sources = [
        {
            'url': 'https://www.airbnb.com/calendar/ical/36870432.ics?s=52f050865b49d6a3f095e1f8bcb2fb0a',
            'cabin': 'Colibri'
        },
        {
            'url': 'https://www.airbnb.com/calendar/ical/1520255215239969187.ics?s=827aa9a5237f3cc3f1a16bb8e72c6e33',
            'cabin': 'Peperina'
        }
    ]
    sync = AirbnbCalendarSync(sources)
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
