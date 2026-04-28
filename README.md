# SANT Digital Solution - School ERP

**Maa Kamala Public School | Rokdi, Karchhana, Prayagraj**

A production-ready, 100% Offline-First School ERP system that runs on a Local Wi-Fi Network (LAN). All data is stored locally using SQLite.

## Features

### Teacher Dashboard & KRA
- **Attendance**: Support for RFID, QR Code, and Manual methods
- **Daily Log**: Subject, Class, Topic, and Image upload for homework
- **KRA Tracking**: Automatic performance tracking (Syllabus %, Attendance %, Homework %)
- **Salary**: Calculated based on KRA scores, attendance, and deductions

### Accountant Module
- Student Admission with auto Roll No and QR code generation
- Fee Collection with search, pending fee tracking, and professional slip printing
- Expenditure Tracker (Lunch, Transport, Office maintenance)

### Principal Dashboard
- Real-time monitoring of Student Logs
- Salary calculation and approval
- Individual WhatsApp alerts for fee dues via `wa.me`
- User management (Teacher/Accountant accounts)

### RFID & Time Management
- RFID on/off toggle
- Configurable time settings for morning and afternoon sessions
- Bulk student attendance via RFID scanners

### Document Generator
- Student ID Cards (printable)
- Admit Cards (Half A4, printable)
- Report Cards (A4, printable)

### Security
- Aadhaar Masking (XXXXXXXX1234) for all roles except Principal
- Aadhaar stored with Fernet encryption
- Role-based access control (Principal, Teacher, Accountant)

## Quick Start

### Prerequisites
- Python 3.9+

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python run.py
```

### Default Login
- **Username**: `principal`
- **Password**: `admin123`

### LAN Access
Other devices on the same Wi-Fi can connect by opening `http://<server-ip>:5000` in their browser.

## Building the Installer (.exe)

### Step 1: Bundle with PyInstaller
```bash
pyinstaller school_erp.spec
```

### Step 2: Create Setup.exe with Inno Setup
1. Install [Inno Setup](https://jrsoftware.org/isinfo.php) on Windows
2. Open `installer/school_erp_setup.iss` in Inno Setup Compiler
3. Click Build > Compile
4. The `Setup.exe` will be created in `installer/Output/`

## Branding
- **Header**: "Maa Kamala Public School | Rokdi, Karchhana, Prayagraj"
- **Footer**: "Developed and Powered by Sant Digital Solution"

## Tech Stack
- **Backend**: Flask (Python)
- **Database**: SQLite (zero-config, local file)
- **Frontend**: Jinja2 + Bootstrap 5
- **Encryption**: cryptography (Fernet)
- **QR Codes**: qrcode + Pillow
- **Packaging**: PyInstaller + Inno Setup

---
*Developed and Powered by Sant Digital Solution*
