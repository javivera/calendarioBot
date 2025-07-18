# � ServidorCalendario Auto-Sync Setup Complete!

Your system now automatically updates **only the servidorCalendario repository** whenever you make, modify, or delete a reservation!

## 📁 Repository Setup

### ServidorCalendario Repository  
- **URL**: https://github.com/javivera/calendario
- **Contains**: Simple calendar server files
- **Calendar Location**: `/calendar.ics` (root level)
- **Purpose**: Dedicated calendar hosting and distribution

## 🔄 Automatic Sync Process

When you perform any reservation operation:

1. **Make/Modify/Delete Reservation** → Triggers sync
2. **Update CSV** → `reservations.csv` updated locally
3. **Generate ICS** → `calendar.ics` files created
4. **Copy to Servidor** → Calendar copied to `servidorCalendario/calendar.ics`
5. **Commit & Push** → ServidorCalendario repository updated on GitHub

## 🌐 Your Calendar URL

### For Public Access:
- **Calendar URL**: `https://javivera.github.io/calendario/calendar.ics`

### For Direct GitHub Access:
- **GitHub URL**: `https://github.com/javivera/calendario/blob/main/calendar.ics`

## 📊 Current Status

- ✅ **Reservations**: 3 total (real reservations only)
- ✅ **Repository**: ServidorCalendario configured and syncing automatically
- ✅ **Auto-Push**: Working perfectly - only pushes to servidorCalendario
- ✅ **Calendar Format**: ICS compatible with all calendar applications

## 🎯 Usage Examples

### Making a New Reservation:
```python
from main import make_reservation

# This will automatically sync to servidorCalendario repository
result = make_reservation('John Doe', '2025-09-01', 500, 5, 'Colibri', 250, '+123456789', 'Vacation booking')
```

### Deleting a Reservation:
```python
from main import delete_reservation

# This will automatically sync to servidorCalendario repository
result = delete_reservation('John Doe')
```

### Modifying a Reservation:
```python
from main import modify_reservation

# This will automatically sync to servidorCalendario repository
result = modify_reservation('John Doe', check_in_date='2025-09-02', total_nights=4)
```

## 🔧 Manual Sync (if needed)

If you ever need to manually sync the calendar:

```bash
python update_calendar_manually.py
```

This will update the servidorCalendario repository with the latest reservation data.

## 🎊 Success!

Your reservation system is now configured for simple, focused automation:

- **Single Repository**: Only servidorCalendario gets updated
- **Automatic Sync**: Every reservation change triggers a push
- **Clean Process**: No dual-repository complexity
- **Reliable**: Focused on the calendar server you actually need

Every reservation change will be automatically reflected in your servidorCalendario repository! 🚀
