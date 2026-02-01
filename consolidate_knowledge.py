#!/usr/bin/env python3
"""
Consolidate all TXT knowledge base files into the CSV database
"""
import csv
from pathlib import Path

KB_DIR = Path("knowledge_base")
CSV_FILE = KB_DIR / "Workplace_IT_Support_Database.csv"

# Read existing CSV
existing_rows = []
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Filter out None keys from malformed CSV
        clean_row = {k: v for k, v in row.items() if k is not None and k.strip()}
        if clean_row:  # Only add non-empty rows
            existing_rows.append(clean_row)

print(f"📊 Existing CSV rows: {len(existing_rows)}")

# New entries to add from TXT files
new_entries = []

# VPN Setup Guide
new_entries.extend([
    {
        "Category": "Network",
        "Issue": "VPN Setup",
        "Question": "How do I connect to the VPN?",
        "Resolution": "1. Download Cisco AnyConnect from https://vpn.acme-corp.com/downloads\n2. Install the app\n3. Connect to vpn.acme-corp.com\n4. Enter your SSO credentials and MFA",
        "Tags": "VPN;Network;AnyConnect;Setup"
    },
    {
        "Category": "Network",  
        "Issue": "VPN Connection",
        "Question": "VPN won't connect",
        "Resolution": "1. Check internet connection\n2. Verify VPN URL is vpn.acme-corp.com\n3. Try disabling firewall temporarily\n4. Clear AnyConnect cache: delete C:\\ProgramData\\Cisco\\Cisco AnyConnect (Windows) or ~/Library/Application Support/Cisco (Mac)",
        "Tags": "VPN;Network;Troubleshooting"
    }
])

# Deep Dive VPN
new_entries.extend([
    {
        "Category": "Network",
        "Issue": "VPN Error 0x80041002",
        "Question": "VPN error code 0x80041002",
        "Resolution": "DNS Resolution Failure. Check if vpn.acme-corp.com resolves. Flush DNS: 'ipconfig /flushdns' (Windows) or 'sudo killall -HUP mDNSResponder' (Mac)",
        "Tags": "VPN;Error;DNS"
    },
    {
        "Category": "Network",
        "Issue": "VPN Error 0x80070057",
        "Question": "VPN error 0x80070057",
        "Resolution": "Invalid parameter/MTU issue. Lower MTU to 1300: 'netsh interface ipv4 set subinterface \"VPN\" mtu=1300 store=persistent'",
        "Tags": "VPN;Error;MTU"
    }
])

# Meeting Room AV
new_entries.extend([
    {
        "Category": "Facility",
        "Issue": "Meeting Room Screen",
        "Question": "How do I share my screen in the meeting room?",
        "Resolution": "Connect the HDMI cable to your laptop or use the wireless 'ShareLink' code displayed on the room's TV screen.",
        "Tags": "Meeting;Facility;Screen;HDMI"
    },
    {
        "Category": "Facility",
        "Issue": "Meeting Room Audio",
        "Question": "How do I unmute the microphone in the meeting room?",
        "Resolution": "Press the microphone button on the Logitech Rally speaker (center of table). LED will turn green when unmuted.",
        "Tags": "Meeting;Facility;Audio;Microphone"
    },
    {
        "Category": "Facility",
        "Issue": "Zoom Room",
        "Question": "How to start a Zoom meeting in the conference room?",
        "Resolution": "Tap 'Start Meeting' on the iPad controller. Or tap 'Join' and enter the meeting ID",
        "Tags": "Meeting;Zoom;Conference"
    }
])

# Laptop Request Policy
new_entries.extend([
    {
        "Category": "Hardware",
        "Issue": "Laptop Request",
        "Question": "How do I request a new laptop?",
        "Resolution": "Submit a request via ServiceNow (https://acme.service-now.com) under Hardware > New Device Request. Include business justification. Approval required from manager and IT.",
        "Tags": "Hardware;Laptop;Request;Policy"
    },
    {
        "Category": "Hardware",
        "Issue": "Laptop Upgrade",
        "Question": "Can I upgrade my laptop?",
        "Resolution": "Laptops are replaced on a 3-year cycle. Early upgrades require VP approval and valid business case (e.g. performance bottleneck for critical work)",
        "Tags": "Hardware;Laptop;Upgrade;Policy"
    }
])

# Hardware Technical Specs
new_entries.extend([
    {
        "Category": "Hardware",
        "Issue": "Cracked Screen",
        "Question": "My screen is cracked",
        "Resolution": "1 accidental damage event covered per year. Submit ticket with photos. AppleCare or Dell ProSupport will arrange repair (typically 2-3 business days)",
        "Tags": "Hardware;Screen;Damage;Repair"
    },
    {
        "Category": "Hardware",
        "Issue": "Standard Laptop Models",
        "Question": "What laptop models are available?",
        "Resolution": "Tier A (Engineering): MacBook Pro 14\" M3 Pro, 36GB RAM. Tier B (Business): MacBook Air 13\" M3 16GB or Dell Latitude 5440",
        "Tags": "Hardware;Laptop;Models;Specs"
    }
])

# Software Security
new_entries.extend([
    {
        "Category": "Software",
        "Issue": "Software Installation",
        "Question": "How do I install software?",
        "Resolution": "Use Self-Service portal (https://self-service.acme-corp.com). Pre-approved software can be installed directly. Custom software requires IT security review (submit ticket)",
        "Tags": "Software;Installation;Security;Policy"
    },
    {
        "Category": "Software",
        "Issue": "Admin Rights",
        "Question": "I need admin rights to install software",
        "Resolution": "Standard users don't have admin rights for security. Use Self-Service portal for approved apps, or submit ticket explaining business need for custom software",
        "Tags": "Software;Admin;Security;Policy"
    }
])

# Printer
new_entries.extend([
    {
        "Category": "Hardware",
        "Issue": "Printer Offline",
        "Question": "My printer is offline",
        "Resolution": "1. Check power - ensure printer screen is on\n2. Verify network - printer should be on 'ACME-Devices' WiFi\n3. Reset queue - delete stuck print jobs and restart printer",
        "Tags": "Printer;Troubleshooting;Offline"
    },
    {
        "Category": "Hardware",
        "Issue": "Printer Paper Jam",
        "Question": "Printer paper jam",
        "Resolution": "Follow on-screen instructions on printer LCD showing jam location (Door A, Tray 2, etc.). Open indicated door and remove jammed paper with both hands. Close firmly.",
        "Tags": "Printer;Troubleshooting;Jam"
    },
    {
        "Category": "Hardware",
        "Issue": "Add Printer",
        "Question": "How do I add a printer?",
        "Resolution": "macOS: System Settings > Printers & Scanners > Add Printer (appears under Bonjour if on corporate WiFi). Windows: Settings > Printers & scanners > Add device",
        "Tags": "Printer;Setup;Installation"
    }
])

# Combine with existing (avoid duplicates by checking Question field)
existing_questions = {row['Question'].lower() for row in existing_rows}
unique_new = [e for e in new_entries if e['Question'].lower() not in existing_questions]

print(f"➕ Adding {len(unique_new)} new Q&A entries from TXT files")

# Write updated CSV
all_rows = existing_rows + unique_new
with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['Category', 'Issue', 'Question', 'Resolution', 'Tags']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"✅ Updated CSV now has {len(all_rows)} total entries")
print(f"📁 Saved to: {CSV_FILE}")
