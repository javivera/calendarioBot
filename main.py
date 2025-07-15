import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
import os
import random

# Your existing reservation functions
def make_reservation(guest_name, check_in_date, cabin,reservation_payed,total_price ,total_nights, cellphone_number="", notes=""):
    print(f"--> Debug: Making reservation for {guest_name} on {check_in_date} for {total_nights} nights.")
    global reservations_df

    if total_nights == 0 and total_price == 0:
        return "Error: Total nights or total price must be provided."
    
    check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
    check_out = check_in + timedelta(days=int(total_nights))

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

    total_price = int(total_nights) * 150

    new_reservation = pd.DataFrame([{
        "guest_names": guest_name,
        "check_in_dates": check_in,
        "check_out_dates": check_out,
        "reservation_payed": reservation_payed,
        "cellphone_numbers": cellphone_number,
        "total_nights": int(total_nights),
        "reservation_total": total_price,
        "notes": notes,
        "cabin": cabin
    }])
    
    reservations_df = pd.concat([reservations_df, new_reservation], ignore_index=True)
    reservations_df.to_csv("reservations.csv", index=False, date_format='%Y-%m-%d')
    
    return f"Successfully created a reservation for {guest_name}."

def delete_reservation(guest_name):
    global reservations_df
    initial_rows = len(reservations_df)
    reservations_df = reservations_df[reservations_df['guest_names'] != guest_name]
    
    if len(reservations_df) < initial_rows:
        reservations_df.to_csv("reservations.csv", index=False)
        return f"Successfully deleted reservation for {guest_name}."
    else:
        return f"Could not find a reservation for {guest_name}."

def modify_reservation(guest_name, check_in_date=None, check_out_date=None, cellphone_number=None, total_nights=None, reservation_total=None, reservation_payed=None, notes=None, cabin=None):
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
    if notes is not None:
        reservations_df.loc[idx, 'notes'] = notes
    if cabin is not None:
        if cabin not in ['Colibri', 'Peperina']:
            return f"Error: Invalid cabin '{cabin}'. Please choose 'Colibri' or 'Peperina'."
        reservations_df.loc[idx, 'cabin'] = cabin
        
    reservations_df.to_csv("reservations.csv", index=False, date_format='%Y-%m-%d')
    return f"Successfully updated reservation for {guest_name}."

def load_reservations():
    try:
        df = pd.read_csv(
            "reservations.csv",
            parse_dates=['check_in_dates', 'check_out_dates']
        )
        if 'total_price' in df.columns:
            df = df.drop(columns=['total_price'])
        return df
    except FileNotFoundError:
        df = pd.DataFrame(columns=[
            'guest_names', 'check_in_dates', 'check_out_dates', 'cellphone_numbers',
            'total_nights', 'reservation_payed', 'reservation_total', 'notes', 'cabin'
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
    numeric_cols = ['total_nights', 'reservation_total', 'reservation_payed']
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

def format_date_spanish(date: datetime) -> str:
    """Formats a datetime object as 'day month' in Spanish (e.g., '14 Julio')."""
    spanish_months = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    day = date.day
    month = spanish_months[date.month]
    return f"{day} de {month}"

reservations_df = load_reservations()

api_key = os.getenv("GEMIMI_API_KEY")
# Configure Gemini API
genai.configure(api_key=api_key)

tools = [make_reservation, delete_reservation, read_the_reservation_schedule, modify_reservation]

system_prompt = f"You are a helpful reservation assistant. Today's date is {datetime.now().strftime('%Y-%m-%d')}. Before making a new reservation, check for existing bookings and ensure no overlaps. Have in mind that check-in and check-out dates are inclusive. Always assume the reservations year is the current year. If there is a conflict, inform the user and do not proceed with the reservation. Use the provided tools to manage reservations. The current reservation schedule is:\n{read_the_reservation_schedule()}. When giving information about reservations, use the format 'day month' in Spanish (e.g., '14 Julio')."

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=tools,
    system_instruction=system_prompt
)

chat = model.start_chat(enable_automatic_function_calling=True)
