#!/usr/bin/env python3
"""
Manual Calendar ICS Update Script
This script manually updates the calendar.ics file from the reservations.csv data.
"""

import pandas as pd
from datetime import datetime, timedelta
import os
import unicodedata
import shutil
import subprocess
import sys


def csv_to_ics():
    """Convert CSV reservations to ICS calendar format and generate per-cabin ICS files.

    Returns the full calendar ICS text (all reservations) as a string. In addition,
    this function writes `servidorCalendario/peperina.ics` and `servidorCalendario/colibri.ics`
    when there are reservations for those cabins.
    """
    
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
    
    # Helper to build ICS from a DataFrame
    def build_ics_from_df(res_df):
        parts = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Cabaña Reservations//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH"
        ]

        for _, reservation in res_df.iterrows():
            check_in = reservation['check_in_dates'].strftime('%Y%m%d')
            check_out = reservation['check_out_dates'].strftime('%Y%m%d')
            guest_name_clean = str(reservation.get('guest_names', '')).replace(' ', '-').replace(',', '')
            uid = f"reservation-{guest_name_clean}-{check_in}@cabana.com"
            summary = f"Reserva: {reservation.get('guest_names', '')} - {reservation.get('cabin', '')}"

            # Build description parts and prefer ARS pricing fields when present
            description_parts = [
                f"Huésped: {reservation.get('guest_names', '')}",
                f"Cabaña: {reservation.get('cabin', '')}",
                f"Noches: {reservation.get('total_nights', '')}"
            ]

            # Determine whether ARS pricing should be used
            def _to_float_safe(v):
                try:
                    if str(v).strip() in ('', 'nan', 'None'):
                        return 0.0
                    return float(v)
                except Exception:
                    return 0.0

            price_per_night_ARS = _to_float_safe(reservation.get('price_per_night_ARS', 0))
            reservation_total_ARS = _to_float_safe(reservation.get('reservation_total_ARS', 0))
            reservation_payed_ARS = _to_float_safe(reservation.get('reservation_payed_ARS', 0))

            has_ars_pricing = (price_per_night_ARS > 0) or (reservation_total_ARS > 0) or (reservation_payed_ARS > 0)

            if has_ars_pricing:
                if price_per_night_ARS > 0:
                    description_parts.append(f"Precio por noche: ${price_per_night_ARS} ARS")
                # Show ARS Total when available
                if reservation_total_ARS > 0:
                    description_parts.append(f"Total: ${reservation_total_ARS} ARS")
                else:
                    # If ARS total not available, attempt to show USD total if present
                    usd_total = reservation.get('reservation_total', '')
                    if str(usd_total).strip() not in ('', 'nan', 'None'):
                        description_parts.append(f"Total: ${usd_total} USD")

                if reservation_payed_ARS > 0:
                    description_parts.append(f"Pagado: ${reservation_payed_ARS} ARS")
                else:
                    paid_usd = reservation.get('reservation_payed', '')
                    description_parts.append(f"Pagado: ${paid_usd} USD")
            else:
                # Fallback to USD pricing
                price_per_night_usd = reservation.get('price_per_night', '')
                description_parts.append(f"Precio por noche: ${price_per_night_usd} USD")
                description_parts.append(f"Total: ${reservation.get('reservation_total', '')} USD")
                description_parts.append(f"Pagado: ${reservation.get('reservation_payed', '')} USD")

            if pd.notna(reservation.get('cellphone_numbers')) and str(reservation.get('cellphone_numbers')).strip():
                description_parts.append(f"Teléfono: {reservation.get('cellphone_numbers')}")
            if pd.notna(reservation.get('notes')) and str(reservation.get('notes')).strip():
                description_parts.append(f"Notas: {reservation.get('notes')}")

            description = "\\n".join(description_parts)

            parts.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART;VALUE=DATE:{check_in}",
                f"DTEND;VALUE=DATE:{check_out}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{reservation.get('cabin', '')} - Cabaña",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                "STATUS:CONFIRMED",
                "TRANSP:OPAQUE",
                "END:VEVENT"
            ])

            print(f"  📅 Added: {reservation.get('guest_names', '')} ({reservation.get('cabin', '')}) - {check_in} to {check_out}")

        parts.append("END:VCALENDAR")
        return '\n'.join(parts)

    # Build full calendar ICS (all reservations)
    full_ics = build_ics_from_df(df)

    # Ensure output directories exist
    create_directories()

    # Generate per-cabin ICS files for Peperina and Colibri (case-insensitive and accent-insensitive)
    def normalize(text: str) -> str:
        """Normalize text by removing accents and lowercasing."""
        if text is None:
            return ""
        # Decompose unicode characters and remove diacritics
        nfkd = unicodedata.normalize('NFKD', str(text))
        only_ascii = ''.join([c for c in nfkd if not unicodedata.combining(c)])
        return only_ascii.strip().lower()

    target_cabins = ['Peperina', 'Colibri']
    normalized_target = {c: normalize(c) for c in target_cabins}

    # Create a normalized cabin column for matching
    df['_cabin_normalized'] = df['cabin'].astype(str).apply(normalize)

    for cabin in target_cabins:
        norm = normalized_target[cabin]
        cabin_df = df[df['_cabin_normalized'] == norm]
        if cabin_df.empty:
            print(f"⚠️  No reservations for {cabin}")
            continue

        cabin_ics = build_ics_from_df(cabin_df)
        cabin_filename = f"servidorCalendario/{normalize(cabin)}.ics"
        try:
            with open(cabin_filename, 'w', encoding='utf-8') as f:
                f.write(cabin_ics)
            print(f"✅ Created {cabin_filename}")
        except Exception as e:
            print(f"❌ Failed to write {cabin_filename}: {e}")

    # Clean up temporary column
    if '_cabin_normalized' in df.columns:
        df.drop(columns=['_cabin_normalized'], inplace=True)

    return full_ics


def create_directories():
    """Create necessary directories if they don't exist"""
    directories = ["static", "servidorCalendario"]
    
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
            
        # Add the updated calendar and per-cabin ICS files
        files_to_add = ['calendar.ics', 'peperina.ics', 'colibri.ics']
        for fname in files_to_add:
            subprocess.run(['git', 'add', fname], cwd=servidor_path)
            print(f"✅ Added {fname} to servidorCalendario git")
        
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
