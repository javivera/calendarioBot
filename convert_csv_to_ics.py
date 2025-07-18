import pandas as pd
from datetime import datetime
import os

def csv_to_ics():
    """Convert CSV reservations to ICS calendar format"""
    
    # Read the CSV file
    try:
        df = pd.read_csv('reservations.csv', parse_dates=['check_in_dates', 'check_out_dates'])
        print(f"Found {len(df)} reservations in CSV file")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
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
        
        print(f"Added: {reservation['guest_names']} ({reservation['cabin']}) - {check_in} to {check_out}")
    
    # ICS file footer
    ics_content.append("END:VCALENDAR")
    
    # Create directories if they don't exist
    os.makedirs("static", exist_ok=True)
    os.makedirs("github-pages-setup", exist_ok=True)
    
    # Write to both locations
    ics_text = '\n'.join(ics_content)
    
    # Write to static folder (for Flask app)
    with open('static/reservations.ics', 'w', encoding='utf-8') as f:
        f.write(ics_text)
    print("✅ Updated static/reservations.ics")
    
    # Write to GitHub Pages setup folder
    with open('github-pages-setup/calendar.ics', 'w', encoding='utf-8') as f:
        f.write(ics_text)
    print("✅ Updated github-pages-setup/calendar.ics")
    
    print(f"\n🎉 Successfully converted {len(df)} reservations to ICS format!")
    return ics_text

if __name__ == "__main__":
    csv_to_ics()
