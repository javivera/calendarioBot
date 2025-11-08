import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
import os
import unicodedata
import random
import subprocess
import shutil
import requests
import re
from dotenv import load_dotenv
import update_calendar

# Load environment variables
load_dotenv()

# Helper to save reservations with desired column order
def save_reservations_file(df):
    """Save reservations.csv enforcing a specific column order.

    Desired order (best-effort; only existing columns are included):
    guest_names, check_in_dates, check_out_dates, price_per_night,
    reservation_payed, reservation_total, total_nights,
    reservation_total_ARS, reservation_payed_ARS, price_per_night_ARS,
    cabin, notes, cellphone_numbers
    Any other columns present will be appended after these.
    """
    try:
        df_to_save = df.copy()
        desired_order = [
            'guest_names', 'check_in_dates', 'check_out_dates', 'price_per_night',
            'reservation_payed', 'reservation_total', 'total_nights',
            'reservation_total_ARS', 'reservation_payed_ARS', 'price_per_night_ARS',
            'cabin', 'notes', 'cellphone_numbers'
        ]

        # Build final column list: include desired columns (if present) in order,
        # then append any other columns that exist in the DataFrame but weren't listed.
        existing_cols = list(df_to_save.columns)
        ordered_cols = [c for c in desired_order if c in existing_cols]
        remaining = [c for c in existing_cols if c not in ordered_cols]
        final_cols = ordered_cols + remaining

        # Reorder DataFrame when appropriate
        if final_cols:
            df_to_save = df_to_save[final_cols]

        df_to_save.to_csv("reservations.csv", index=False, date_format='%Y-%m-%d')
        print("✅ Saved reservations.csv with enforced column order")
    except Exception as e:
        print(f"❌ Error saving reservations file: {e}")


def parse_date_input(date_str):
    """Parse user-provided date strings in several common formats.

    Accepts datetime objects and strings in formats like:
    - 'YYYY-MM-DD'
    - 'DD/MM/YYYY' or 'DD-MM-YYYY'
    - 'DD/MM/YY'
    - 'DD/MM' (assumes current year, or next year if date already passed)

    Raises ValueError if parsing fails.
    """
    if isinstance(date_str, datetime):
        return date_str

    s = str(date_str).strip()
    if not s:
        raise ValueError("Empty date string")

    # Try common formats
    formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d %B %Y', '%d %b %Y']
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue

    # Try dd/mm without year
    m = re.match(r'^(\d{1,2})[\/-](\d{1,2})$', s)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        now = datetime.now()
        year = now.year
        try:
            candidate = datetime(year, month, day)
        except Exception:
            raise ValueError(f"Invalid date components in '{s}'")
        # If candidate already passed, assume next year
        if candidate < now:
            candidate = datetime(year + 1, month, day)
        return candidate

    raise ValueError(f"Could not parse date '{s}'. Expected formats like YYYY-MM-DD or DD/MM/YYYY")

# === CALENDAR SYNC FUNCTIONS (formerly git_calendar_sync.py) ===
def csv_to_ics():
    """Convert CSV reservations to ICS calendar format and generate per-cabin ICS files.

    Writes `servidorCalendario/calendar.ics` (all reservations) and
    `servidorCalendario/peperina.ics` and `servidorCalendario/colibri.ics` when
    reservations exist for those cabins.
    Returns the full calendar ICS text.
    """
    # Read the CSV file
    try:
        df = pd.read_csv('reservations.csv', parse_dates=['check_in_dates', 'check_out_dates'])
        print(f"Found {len(df)} reservations in CSV file")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    if df.empty:
        print("⚠️  No reservations found in CSV file")
        return ""

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
            guest_name_clean = reservation['guest_names'].replace(' ', '-').replace(',', '')
            uid = f"reservation-{guest_name_clean}-{check_in}@cabana.com"
            summary = f"Reserva: {reservation['guest_names']} - {reservation['cabin']}"

            description_parts = [
                f"Huésped: {reservation['guest_names']}",
                f"Cabaña: {reservation['cabin']}",
                f"Noches: {reservation['total_nights']}"
            ]

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
                if reservation_total_ARS > 0:
                    description_parts.append(f"Total: ${reservation_total_ARS} ARS")
                else:
                    usd_total = reservation.get('reservation_total', '')
                    if str(usd_total).strip() not in ('', 'nan', 'None'):
                        description_parts.append(f"Total: ${usd_total} USD")
                if reservation_payed_ARS > 0:
                    description_parts.append(f"Pagado: ${reservation_payed_ARS} ARS")
                else:
                    description_parts.append(f"Pagado: ${reservation.get('reservation_payed')} USD")
            else:
                description_parts.append(f"Precio por noche: ${reservation.get('price_per_night', 150)} USD")
                description_parts.append(f"Total: ${reservation['reservation_total']} USD")
                description_parts.append(f"Pagado: ${reservation['reservation_payed']} USD")

            if pd.notna(reservation['cellphone_numbers']) and str(reservation['cellphone_numbers']).strip():
                description_parts.append(f"Teléfono: {reservation['cellphone_numbers']}")
            if pd.notna(reservation['notes']) and str(reservation['notes']).strip():
                description_parts.append(f"Notas: {reservation['notes']}")

            description = "\\n".join(description_parts)

            parts.extend([
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

            print(f"Added: {reservation['guest_names']} ({reservation['cabin']}) - {check_in} to {check_out}")

        parts.append("END:VCALENDAR")
        return '\n'.join(parts)

    # Build full calendar ICS (all reservations)
    full_ics = build_ics_from_df(df)

    # Ensure output directory exists
    os.makedirs("servidorCalendario", exist_ok=True)

    # Write full calendar
    try:
        with open('servidorCalendario/calendar.ics', 'w', encoding='utf-8') as f:
            f.write(full_ics)
        print("✅ Updated servidorCalendario/calendar.ics")
    except Exception as e:
        print(f"❌ Failed to write servidorCalendario/calendar.ics: {e}")

    # Generate per-cabin ICS files (case-insensitive and accent-insensitive)
    def normalize(text: str) -> str:
        if text is None:
            return ""
        nfkd = unicodedata.normalize('NFKD', str(text))
        return ''.join([c for c in nfkd if not unicodedata.combining(c)]).strip().lower()

    target_cabins = ['Peperina', 'Colibri']
    normalized_target = {c: normalize(c) for c in target_cabins}
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

    if '_cabin_normalized' in df.columns:
        df.drop(columns=['_cabin_normalized'], inplace=True)

    print(f"\n🎉 Successfully converted {len(df)} reservations to ICS format!")
    return full_ics

def update_calendar_and_push():
    """
    Updates the ICS calendar file and pushes changes to servidorCalendario repository only
    """
    try:
        # Generate updated ICS file directly in servidorCalendario folder
        print("🔄 Updating calendar.ics...")
        csv_to_ics()
        
        # Push to servidorCalendario repository
        return push_to_servidor_repository()
        
    except Exception as e:
        print(f"❌ Error updating calendar: {e}")
        return False

def push_to_servidor_repository():
    """
    Push changes to the servidorCalendario repository
    """
    original_cwd = None
    print("\n📁 Pushing to servidorCalendario repository...")

    servidor_path = "servidorCalendario"

    # Check if servidorCalendario directory exists
    if not os.path.exists(servidor_path):
        print("❌ servidorCalendario directory not found")
        return False

    # Check if it's a git repository (run from the repo path)
    result = subprocess.run(['git', 'status'], capture_output=True, text=True, cwd=servidor_path)
    if result.returncode != 0:
        print("❌ servidorCalendario is not a git repository")
        return False

    try:
        # Change into the servidorCalendario directory and run git commands there
        original_cwd = os.getcwd()
        os.chdir(servidor_path)

        # Refresh git status locally
        status = subprocess.run(['git', 'status'], capture_output=True, text=True)
        if status.returncode != 0:
            print("❌ git status failed inside servidorCalendario")
            return False

        # Add all changes (calendar and per-cabin ICS files or any other changes)
        add_result = subprocess.run(['git', 'add', '.'], capture_output=True, text=True)
        if add_result.returncode == 0:
            print("✅ Staged all changes in servidorCalendario (git add .)")
        else:
            print(f"❌ git add failed: {add_result.stderr}")
            return False

        # Create commit message with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Auto-update calendar: {timestamp}"

        # Commit the changes
        commit = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True)

        if commit.returncode == 0:
            print(f"✅ Committed changes to servidorCalendario: {commit_message}")

            # Push to GitHub (force push to overwrite remote if necessary)
            push_result = subprocess.run(['git', 'push'], capture_output=True, text=True)
            print(push_result)

            if push_result.returncode == 0:
                print("🚀 Successfully pushed to servidorCalendario repository!")
                return True
            else:
                print(f"❌ Failed to push to servidorCalendario repository: {push_result.stderr}")
                return False
        else:
            # If there is nothing to commit, git returns exit code 1 but stdout/stderr contains helpful text
            combined = (commit.stdout or "") + (commit.stderr or "")
            if "nothing to commit" in combined.lower() or "no changes added to commit" in combined.lower():
                print("ℹ️  No changes to commit in servidorCalendario repository")
                return True
            else:
                print(f"❌ Failed to commit to servidorCalendario repository: {combined}")
                return False
    except Exception as e:
        print(f"❌ Error pushing to servidorCalendario repository: {e}")
        return False
    finally:
        # Restore original working directory if it exists
        try:
            if original_cwd:
                os.chdir(original_cwd)
        except Exception:
            pass

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

def day_month_spanish() -> str:
    """
    Return the current date and time in Spanish format.

    Example: '20 de Agosto de 2025 18:35:12'
    """
    months_es = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    now = datetime.now()
    day = now.day
    month = months_es[now.month - 1]
    year = now.year
    time_str = now.strftime("%H:%M:%S")
    return f"{day} de {month} de {year} {time_str}"

# === RESERVATION MANAGEMENT FUNCTIONS ===
def make_reservation(guest_name, check_in_date, cabin, total_nights, cellphone_number="", notes="", price_per_night=0, price_per_night_ARS=0, reservation_total_ARS=0, total_price=0, reservation_payed_ARS=0,reservation_payed=0):
    print(f"--> Debug: Making reservation for {guest_name} on {check_in_date} for {total_nights} nights.")
    global reservations_df
    # Normalize and validate inputs
    try:
        check_in = parse_date_input(check_in_date)
    except Exception as e:
        return f"Error parsing check-in date: {e}"

    try:
        total_nights = int(float(total_nights))
    except Exception:
        total_nights = 0

    if total_nights == 0 and not total_price:
        return "Error: Total nights or total price must be provided."

    check_out = check_in + timedelta(days=int(total_nights))

    # Initialize calculated price variables to safe defaults to avoid unbound variables
    calculated_price_per_night = float(price_per_night) if price_per_night is not None else 150.0
    calculated_price_per_night_ARS = float(price_per_night_ARS) if price_per_night_ARS is not None else 0.0
    calculated_reservation_total_ARS = float(reservation_total_ARS) if reservation_total_ARS is not None else 0.0

    overlapping_reservations = reservations_df[
        (reservations_df['check_in_dates'] < check_out) & 
        (reservations_df['check_out_dates'] > check_in)
    ]


    overlapping_reservations = reservations_df[
        (reservations_df['check_in_dates'] < check_out) & 
        (reservations_df['check_out_dates'] > check_in) &
        (reservations_df['cabin'] == cabin)
    ]

    if not overlapping_reservations.empty:
        conflicts = overlapping_reservations[['guest_names', 'check_in_dates', 'check_out_dates']].copy()
        conflicts['check_in_dates'] = conflicts['check_in_dates'].dt.strftime('%Y-%m-%d')
        conflicts['check_out_dates'] = conflicts['check_out_dates'].dt.strftime('%Y-%m-%d')
        return f"Could not make reservation. The dates conflict with the following booking(s):\n{conflicts.to_string(index=False)}"

    # Calculate total price based on price_per_night if provided, otherwise use default $150
    try:
        if price_per_night is not None and str(price_per_night).strip() != '':
            calculated_price_per_night = float(price_per_night)
        else:
            calculated_price_per_night = 150.0
        total_price = int(total_nights) * calculated_price_per_night
        print(f"--> Debug: Using price per night: ${calculated_price_per_night} x {total_nights} nights = ${total_price}")
    except Exception:
        calculated_price_per_night = 150.0
        total_price = int(total_nights) * calculated_price_per_night
    # else:
        # calculated_price_per_night = 0
        # total_price = int(total_nights) * 150
        # print(f"--> Debug: Using default price per night: $150 x {total_nights} nights = ${total_price}")

    # Calculate ARS pricing if provided
    try:
        if price_per_night_ARS is not None and str(price_per_night_ARS).strip() != '':
            calculated_price_per_night_ARS = float(price_per_night_ARS)
        else:
            calculated_price_per_night_ARS = 0.0
        calculated_reservation_total_ARS = int(total_nights) * calculated_price_per_night_ARS
        if calculated_price_per_night_ARS > 0:
            print(f"--> Debug: Using ARS price per night: ${calculated_price_per_night_ARS} x {total_nights} nights = ${calculated_reservation_total_ARS}")
    except Exception:
        calculated_price_per_night_ARS = 0.0
        calculated_reservation_total_ARS = 0.0
    # else:
    #     calculated_price_per_night_ARS = 0.0
    #     calculated_reservation_total_ARS = 0

    new_reservation = pd.DataFrame([{
        "guest_names": guest_name,
        "check_in_dates": check_in,
        "check_out_dates": check_out,
        "cellphone_numbers": cellphone_number,
        "total_nights": int(total_nights),
        "reservation_total": total_price,
        "reservation_payed": reservation_payed,
        "price_per_night": calculated_price_per_night,
        "reservation_total_ARS": calculated_reservation_total_ARS,
        "reservation_payed_ARS": float(reservation_payed_ARS),
        "price_per_night_ARS": calculated_price_per_night_ARS,
        "notes": notes,
        "cabin": cabin
    }])
    
    reservations_df = pd.concat([reservations_df, new_reservation], ignore_index=True)
    save_reservations_file(reservations_df)
    
    # Auto-update calendar and push to GitHub
    try:
        success = update_calendar_and_push()
        if success:
            print("🎉 Calendar updated and pushed to GitHub!")
        else:
            print("⚠️  Calendar update failed, but reservation was saved.")
    except Exception as e:
        print(f"⚠️  Auto-sync error: {e}")
    
    return f"Successfully created a reservation for {guest_name}."

def delete_reservation(guest_name):
    global reservations_df
    initial_rows = len(reservations_df)
    reservations_df = reservations_df[reservations_df['guest_names'] != guest_name]
    
    if len(reservations_df) < initial_rows:
        save_reservations_file(reservations_df)
        
        # Auto-update calendar and push to GitHub
        try:
            success = update_calendar_and_push()
            if success:
                print("🎉 Calendar updated and pushed to GitHub!")
            else:
                print("⚠️  Calendar update failed, but reservation was deleted.")
        except Exception as e:
            print(f"⚠️  Auto-sync error: {e}")
        
        return f"Successfully deleted reservation for {guest_name}."
    else:
        return f"Could not find a reservation for {guest_name}."

def modify_reservation(guest_name, check_in_date=None, check_out_date=None, cellphone_number=None, total_nights=None, reservation_total=None, reservation_payed=None, notes=None, cabin=None, price_per_night=None, reservation_total_ARS=None, reservation_payed_ARS=None, price_per_night_ARS=None):
    global reservations_df
    
    # Find the reservation by guest_name
    reservation_index = reservations_df[reservations_df['guest_names'] == guest_name].index
    
    if reservation_index.empty:
        return f"Could not find a reservation for {guest_name}."
    
    idx = reservation_index[0] # Assuming guest names are unique for simplicity
    
    # Update fields if provided
    if check_in_date:
        reservations_df.loc[idx, 'check_in_dates'] = pd.to_datetime(check_in_date)
    if check_out_date:
        reservations_df.loc[idx, 'check_out_dates'] = pd.to_datetime(check_out_date)
    if cellphone_number is not None:
        reservations_df.loc[idx, 'cellphone_numbers'] = cellphone_number
    if total_nights is not None:
        reservations_df.loc[idx, 'total_nights'] = int(total_nights)
    if reservation_total is not None:
        reservations_df.loc[idx, 'reservation_total'] = float(reservation_total)
    if reservation_payed is not None:
        reservations_df.loc[idx, 'reservation_payed'] = float(reservation_payed)
    if price_per_night is not None:
        reservations_df.loc[idx, 'price_per_night'] = float(price_per_night)
    if reservation_total_ARS is not None:
        reservations_df.loc[idx, 'reservation_total_ARS'] = float(reservation_total_ARS)
    if reservation_payed_ARS is not None:
        reservations_df.loc[idx, 'reservation_payed_ARS'] = float(reservation_payed_ARS)
    if price_per_night_ARS is not None:
        reservations_df.loc[idx, 'price_per_night_ARS'] = float(price_per_night_ARS)
    if notes is not None:
        reservations_df.loc[idx, 'notes'] = notes
    if cabin is not None:
        if cabin not in ['Colibri', 'Peperina']:
            return f"Error: Invalid cabin '{cabin}'. Please choose 'Colibri' or 'Peperina'."
        reservations_df.loc[idx, 'cabin'] = cabin
        
    save_reservations_file(reservations_df)
    
    # Auto-update calendar and push to GitHub
    try:
        success = update_calendar_and_push()
        if success:
            print("🎉 Calendar updated and pushed to GitHub!")
        else:
            print("⚠️  Calendar update failed, but reservation was modified.")
    except Exception as e:
        print(f"⚠️  Auto-sync error: {e}")
    
    return f"Successfully updated reservation for {guest_name}."

def load_reservations():
    try:
        df = pd.read_csv(
            "reservations.csv",
            parse_dates=['check_in_dates', 'check_out_dates']
        )
        if 'total_price' in df.columns:
            df = df.drop(columns=['total_price'])
        
        # Add price_per_night column if it doesn't exist (for backward compatibility)
        if 'price_per_night' not in df.columns:
            df['price_per_night'] = 150.0  # Default rate for existing reservations
        
        # Add ARS columns if they don't exist (for backward compatibility)
        if 'reservation_total_ARS' not in df.columns:
            df['reservation_total_ARS'] = 0.0
        if 'reservation_payed_ARS' not in df.columns:
            df['reservation_payed_ARS'] = 0.0
        if 'price_per_night_ARS' not in df.columns:
            df['price_per_night_ARS'] = 0.0
            
        return df
    except FileNotFoundError:
        df = pd.DataFrame(columns=[
            'guest_names', 'check_in_dates', 'check_out_dates', 'cellphone_numbers',
            'total_nights', 'reservation_total', 'reservation_payed', 'price_per_night', 
            'reservation_total_ARS', 'reservation_payed_ARS', 'price_per_night_ARS', 'notes', 'cabin'
        ])
        df['check_in_dates'] = pd.to_datetime(df['check_in_dates'])
        df['check_out_dates'] = pd.to_datetime(df['check_out_dates'])
        return df

def read_the_reservation_schedule() -> str:
    try:
        df = pd.read_csv("reservations.csv")
        if df.empty:
            return "The reservation schedule is currently empty. There are no bookings."
        return df.to_string(index=False)
    except FileNotFoundError:
        return "Error: The reservations file could not be found."

def get_all_reservations() -> list:
    """
    Retrieves all reservations from the CSV file.
    """
    global reservations_df
    if reservations_df.empty:
        return []
    
    # Ensure date columns are datetime objects before returning
    reservations_df['check_in_dates'] = pd.to_datetime(reservations_df['check_in_dates'], errors='coerce')
    reservations_df['check_out_dates'] = pd.to_datetime(reservations_df['check_out_dates'], errors='coerce')
    
    # Fill NaN values with None for JSON compatibility
    # Identify numeric columns that might contain NaN
    numeric_cols = ['total_nights', 'reservation_total', 'reservation_payed', 'price_per_night', 
                   'reservation_total_ARS', 'reservation_payed_ARS', 'price_per_night_ARS']
    for col in numeric_cols:
        if col in reservations_df.columns:
            reservations_df[col] = reservations_df[col].fillna(pd.NA).where(pd.notna(reservations_df[col]), None)
    
    # Handle 'cellphone_numbers' specifically if it can be empty and cause issues
    if 'cellphone_numbers' in reservations_df.columns:
        reservations_df['cellphone_numbers'] = reservations_df['cellphone_numbers'].fillna('') # Fill empty strings for phone numbers
    
    return reservations_df.to_dict('records')

def get_next_three_reservations() -> list:
    """
    Retrieves the first three reservations sorted by check-in date,
    returning guest name, check-in date, and check-out date in Spanish 'day month' format.
    """
    global reservations_df
    print(f"--> Debug: Running get_next_three_reservations - DataFrame size: {len(reservations_df)}")
    if reservations_df.empty:
        print("--> Debug: No reservations in DataFrame")
        return []

    try:
        # Ensure date columns are datetime
        reservations_df['check_in_dates'] = pd.to_datetime(reservations_df['check_in_dates'], errors='coerce')
        reservations_df['check_out_dates'] = pd.to_datetime(reservations_df['check_out_dates'], errors='coerce')
        # Select reservations and sort by check-in date
        upcoming = reservations_df[['guest_names', 'check_in_dates', 'check_out_dates', 'cabin']].copy()
        upcoming = upcoming.sort_values(by='check_in_dates').head(3)
        print(f"--> Debug: Selected {len(upcoming)} reservations")
        print(f"--> Debug: Selected reservations:\n{upcoming.to_string()}")
        # Format dates as Spanish 'day month'
        upcoming['check_in_dates'] = upcoming['check_in_dates'].apply(lambda x: format_date_spanish(x) if pd.notnull(x) else 'Invalid Date')
        upcoming['check_out_dates'] = upcoming['check_out_dates'].apply(lambda x: format_date_spanish(x) if pd.notnull(x) else 'Invalid Date')
        # Drop any rows with invalid dates
        upcoming = upcoming[upcoming['check_in_dates'] != 'Invalid Date']
        upcoming = upcoming[upcoming['check_out_dates'] != 'Invalid Date']
        print(f"--> Debug: After dropping invalid dates, {len(upcoming)} reservations remain")
        return upcoming.to_dict('records')
    except Exception as e:
        print(f"--> Debug: Error in get_next_three_reservations: {str(e)}")
        return []

# === CALENDAR LINK FUNCTIONS ===
def format_date_spanish(date: datetime) -> str:
    """Formats a datetime object as 'day month' in Spanish (e.g., '14 Julio')."""
    spanish_months = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    day = date.day
    month = spanish_months[date.month]
    return f"{day} de {month}"

def generate_ics_file():
    """
    Generates an .ics (iCalendar) file with all reservations.
    """
    global reservations_df
    
    if reservations_df.empty:
        return "No reservations to export."
    
    # ICS file header
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Cabaña Reservations//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    for _, reservation in reservations_df.iterrows():
        # Format dates for ICS (YYYYMMDD format)
        check_in = reservation['check_in_dates'].strftime('%Y%m%d')
        check_out = reservation['check_out_dates'].strftime('%Y%m%d')
        
        # Create a unique ID for the event
        uid = f"reservation-{reservation['guest_names'].replace(' ', '-')}-{check_in}@cabana.com"
        
        # Create event summary
        summary = f"Reserva: {reservation['guest_names']} - {reservation['cabin']}"
        
        # Create description with all details
        description = f"Huésped: {reservation['guest_names']}\\n"
        description += f"Cabaña: {reservation['cabin']}\\n"
        description += f"Noches: {reservation['total_nights']}\\n"
        description += f"Precio por noche: ${reservation.get('price_per_night', 150)}\\n"
        description += f"Total: ${reservation['reservation_total']}\\n"
        description += f"Pagado: ${reservation['reservation_payed']}\\n"
        
        # Add ARS pricing if available
        if reservation.get('price_per_night_ARS', 0) > 0:
            description += f"Precio por noche (ARS): ${reservation.get('price_per_night_ARS', 0)}\\n"
        if reservation.get('reservation_total_ARS', 0) > 0:
            description += f"Total (ARS): ${reservation.get('reservation_total_ARS', 0)}\\n"
        if reservation.get('reservation_payed_ARS', 0) > 0:
            description += f"Pagado (ARS): ${reservation.get('reservation_payed_ARS', 0)}\\n"
        
        if pd.notna(reservation['cellphone_numbers']) and reservation['cellphone_numbers']:
            description += f"Teléfono: {reservation['cellphone_numbers']}\\n"
        
        if pd.notna(reservation['notes']) and reservation['notes']:
            description += f"Notas: {reservation['notes']}\\n"
        
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
    
    # ICS file footer
    ics_content.append("END:VCALENDAR")
    
    # Write to file
    ics_file_path = "static/reservations.ics"
    os.makedirs("static", exist_ok=True)
    
    with open(ics_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ics_content))
    
    return f"ICS file generated successfully at {ics_file_path}"

def get_calendar_link():
    """
    Get the calendar link for viewing reservations online
    """
    calendar_url = "https://javivera.github.io/calendario/"
    calendar_ics_url = "https://javivera.github.io/calendario/calendar.ics"
    
    return (
        f"📅 **Calendario de Reservas - Cabañas Las Chacras**\n\n"
        f"🌐 {calendar_url}\n\n"
    )

def get_dollar_price():
    """Fetch the 'contado con liqui' dollar price from dolarapi.com and return a concise dict.

    Returns: dict with keys: success(bool), buy(float|None), sell(float|None), raw(dict|list)
    """
    url = "https://dolarapi.com/v1/dolares/contadoconliqui"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Accept either list or dict
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            return {"success": False, "error": "Unexpected API response format", "raw": data}

        # Normalize fields
        buy = item.get('compra') or item.get('buy') or item.get('valor_compra')
        sell = item.get('venta') or item.get('sell') or item.get('valor_venta')

        def _to_float(v):
            if v is None:
                return None
            if isinstance(v, (int, float)):
                return float(v)
            try:
                s = str(v).replace('.', '').replace(',', '.')
                return float(s)
            except Exception:
                return None

        buy_f = _to_float(buy)
        sell_f = _to_float(sell)

        return {"success": True, "buy": buy_f, "sell": sell_f, "raw": item}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === MAIN PROGRAM ===
reservations_df = load_reservations()

api_key = os.getenv("GEMIMI_API_KEY")
if not api_key:
    raise ValueError("GEMIMI_API_KEY environment variable not set")

# Configure Gemini API
genai.configure(api_key=api_key)

def gemini_update_calendar(push_to_git: bool = False):
    """
    Safe wrapper for gemini_update_calendar exposed to Gemini.

    - Logs calls to `assistant_audit.log` with a timestamp and the result.
    - Requires `push_to_git=True` to perform git pushes; default is False.
    - Returns a simple dict suitable for tool-based responses: {"success": bool, "message": str}.
    """
    _ts = None
    try:
        audit_path = "assistant_audit.log"
        from datetime import datetime as _dt
        _ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(audit_path, "a", encoding="utf-8") as _f:
            _f.write(f"{_ts} - gemini_update_calendar called with push_to_git={push_to_git}\n")

        # Call the underlying function with an explicit argument
        result = gemini_update_calendar(push_to_git=push_to_git)

        msg = "Pushed to git" if result else "Updated calendar (no push or push failed)"
        with open(audit_path, "a", encoding="utf-8") as _f:
            _f.write(f"{_ts} - result: {result}\n")

        return {"success": bool(result), "message": msg}
    except Exception as e:
        try:
            with open("assistant_audit.log", "a", encoding="utf-8") as _f:
                _f.write(f"{_ts} - exception: {e}\n")
        except Exception:
            pass
        return {"success": False, "message": str(e)}


tools = [
    make_reservation,
    delete_reservation,
    read_the_reservation_schedule,
    modify_reservation,
    get_calendar_link,
    day_month_spanish,
    get_dollar_price,
    gemini_update_calendar,
]

system_prompt = f"""You are a helpful reservation assistant for Cabañas Las Chacras. In order to check today's date 
is you can use day_month_spanish function. Before making a new reservation, check for existing bookings and ensure 
no overlaps (unless check-in and check-out dates are the same). If at any point the user asks to make a reservation 
for a date that its a check-out inform the user the date is available but he should take note that someone is going out 
that day and then proceed to make the reservation. Always assume the reservations year is the current year unless the date 
provided is in the past (before the current date) in that case assume its for the next year. If there is a conflict, 
inform the user and do not proceed with the reservation. Use the provided tools to manage reservations. Have in mind 
that the amount of nights is the difference between check-in and check-out dates. Before performing any function call 
present the user with appropiate information and ask for confirmation. The current reservation schedule 
is:\n{read_the_reservation_schedule()}. When giving information about reservations, use the format 'day month' in 
Spanish (e.g., '14 Julio'). When answering be concise and to the point. Have in mind that sometimes currency will be in 
argentinian pesos (ARS) and sometimes un dollars (USD). If the number is more than 3 digits its probably in pesos, 
but when in doubt ask the user which currency he is referring to. Try to give short informative answers. And sometimes,
not always, when ending a conversation say a reasuring phrase like 'No te preocupes, todo está bajo control.' or 
'Todo está bien, no hay de qué preocuparse.'. If the user asks for the calendar link, calendar, or wants to see 
reservations online, use the get_calendar_link function to provide them with the calendar website link. When making a 
new reservation you should always, NO EXCEPTION, ask for: guest name, check-in date and cabin name (cabin name will be peperina or colibri.. 
if the user asks for sometin simillar and its a typo just correct it.. if you are not sure which cabin is being referenced, ask the user), 
always ask for all this, dont assume. Then you either need a check out date or the total nights in which case you can calculate 
the check-out date. Then you need total price (in ARS or USD) or price per night in wich case you can calculate the 
total price using total nights. If no reservation_payed is given you should ask if there was any made in anticipation.
Before making any reservation of modification always present the user with the pertinent information and ask for confrimation. 
if you need to get dolar peso price use the get_dollar_price function. If the user tells you theres been a new reservation on airbnb you 
should run gemini_update_calendar and report back the result to the user. Always confirm actions before executing them."""

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=tools,
    system_instruction=system_prompt
)

chat = model.start_chat(enable_automatic_function_calling=True)
