# IT Support Guide

Nimbus Technologies IT team. Last updated September 2026. This guide answers the most common IT questions. If you can't find what you need, contact the IT helpdesk.

## Contacting the IT helpdesk

- **ServiceDesk portal:** servicedesk.nimbus.example (fastest; track your ticket here)
- **Email:** it-help@nimbus.example
- **Phone:** extension **4357** (H-E-L-P) from any office phone, or 080-4710-4357 from outside
- **Walk-in:** IT desk on the 2nd floor of each office, 9:00 AM to 7:00 PM, Monday to Friday

The helpdesk is staffed 24x7 for critical issues (for example, you can't work at all). Response targets: critical issues 30 minutes, everything else 4 business hours.

### How to raise an IT ticket

1. Go to servicedesk.nimbus.example and sign in with your Nimbus account.
2. Choose **Report a problem** (something is broken) or **Request something** (access, hardware, software).
3. Describe the issue, add screenshots, and set the urgency.
4. You'll get a ticket number by email. Reply to that email to add information.

## Passwords and accounts

### Resetting your password

Use the self-service portal at **password.nimbus.example**. You can reset your password from any browser using Microsoft Authenticator approval or an SMS code to your registered mobile number. If you are locked out and self-service fails, call the helpdesk on extension 4357; you'll need to verify your identity with your employee ID and manager's name.

Your password must have at least 12 characters, including upper-case, lower-case and a number or symbol. Passwords expire every **90 days** and you can't reuse your last 5 passwords. You'll get reminder emails 14 days before expiry.

The same password is used for email, VPN, PeopleHub and Wi-Fi (single sign-on), so changing it in one place changes it everywhere.

### Multi-factor authentication (MFA)

MFA is mandatory. Install **Microsoft Authenticator** on your phone and register it at aka.nimbus.example/mfa during your first day. If you change phones, register the new phone before resetting the old one; otherwise call the helpdesk.

## VPN (remote access)

### Connecting to the VPN from home

Nimbus uses **GlobalProtect** VPN. It's pre-installed on all company laptops.

1. Connect to your home internet.
2. Click the GlobalProtect icon in the system tray (Windows) or menu bar (Mac).
3. The portal address is **vpn.nimbus.example**. Click **Connect**.
4. Sign in with your Nimbus email and password, then approve the Microsoft Authenticator prompt.
5. The icon turns into a shield with a check mark when you're connected.

You need the VPN for internal systems (Jira, the shared drive, the build servers). Email, Slack and PeopleHub work without VPN.

### If the VPN keeps disconnecting

- Make sure you're on a stable connection; mobile hotspots often drop the VPN. Prefer Wi-Fi or Ethernet.
- Disconnect and reconnect, choosing a different gateway (Bengaluru, Pune or Mumbai) from the GlobalProtect settings.
- Restart the laptop; pending Windows updates often cause disconnects.
- The VPN disconnects automatically after 12 hours; just reconnect.
- If it still drops more than twice an hour, raise a ticket with the time of each disconnect.

## Email and phone setup

### Setting up email on your phone

Company email on phones is only allowed through the **Microsoft Outlook** app, managed by **Intune**.

1. Install **Intune Company Portal** from the App Store or Play Store and sign in with your Nimbus account.
2. Follow the prompts to register the device (this applies a work profile; IT cannot see your personal photos, messages or apps).
3. Install **Microsoft Outlook** and sign in. Your mailbox, calendar and contacts will sync.

### Outlook not syncing

Check that you're online and that Outlook isn't in offline mode (Send/Receive tab). Restart Outlook. If your mailbox is near its 50 GB limit, archive old mail. On phones, open Company Portal and tap **Check status**. If it still doesn't sync, raise a ticket.

## Laptops and hardware

### Standard equipment

Every employee receives a laptop (Dell Latitude 14 or MacBook Air for designers and mobile engineers), a headset, and a laptop bag. Monitors are available at every office desk.

### Requesting a new monitor or accessories

Request an external monitor, keyboard, mouse or docking station for home on ServiceDesk under **Request something > Hardware**. A second monitor for home use needs your manager's approval. Standard accessories are delivered within 5 working days.

### Laptop upgrades and replacements

Laptops are replaced every **4 years**. If your laptop is too slow for your work before then, raise a **Laptop upgrade** request on ServiceDesk with a short business justification; your manager and the IT Manager approve it. Engineers needing more memory (32 GB) can request an upgrade after 2 years.

### If your laptop is not working

Restart it first. If it won't start, has a broken screen or keyboard, or is very slow, raise a critical ticket or call extension 4357. The helpdesk can lend you a spare laptop the same day while yours is repaired.

### Lost or stolen laptop or phone

Report a lost or stolen company laptop or phone to the helpdesk **within 1 hour** by calling extension 4357 (24x7), so IT can lock and wipe it remotely. Also file a police complaint (FIR) and upload a copy to the ticket within 3 days; it's needed for insurance. You won't be charged for a stolen device if it was reported promptly.

## Software

### Installing software

Install approved software yourself from **Company Portal** (Windows) or **Self Service** (Mac). Over 200 approved apps are available, including VS Code, Docker Desktop, Zoom, Figma and Postman. For software that isn't listed, raise a **Software request** on ServiceDesk with the product name and why you need it; the Security team reviews it within 3 working days. You don't have admin rights on your laptop, so installer files downloaded from the internet won't run.

### Licences

Paid licences (for example JetBrains IDEs or Adobe Creative Cloud) need manager approval and are assigned by IT. Licences unused for 60 days are reclaimed.

## Network and Wi-Fi

- **NIMBUS-CORP**: for company laptops; connects automatically using your Nimbus account.
- **NIMBUS-GUEST**: for visitors and personal devices. The guest Wi-Fi password changes every day and is available at reception and on the screen at the office entrance. Guest Wi-Fi is internet-only and can't reach internal systems.

## Shared drives and access

To get access to a shared drive, Jira project or other internal system, raise an **Access request** on ServiceDesk and name the system and the access level. The owner of the drive or system approves it; access is usually granted within 1 working day. Access is removed automatically when you change teams.

## Printers

Each floor has a multi-function printer. Send print jobs to **Nimbus-Print**, then tap your ID card on the printer to release them. Colour printing is limited to 100 pages a month. If a printer is jammed or out of toner, report it to the Admin team at reception or on ServiceDesk under **Facilities**.

## ID cards and office access

Your ID card also works as your access card for the office doors and printers. If your card stops working or is lost, contact the **Admin/Facilities desk** at reception (not IT) or email facilities@nimbus.example. A lost card is blocked immediately and a replacement costs INR 300, deducted from salary. A temporary card is issued the same day.
