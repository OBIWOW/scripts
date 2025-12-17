#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 16:40:14 2025

Create email drafts for OBiWoW participants (Apple mail app), send as bcc

@author: ekaterinaavershina
"""

import pandas as pd
import subprocess as sp
import argparse

parser = argparse.ArgumentParser(description='Create Apple Mail drafts for workshops from a registration table')

parser.add_argument('-i','--input',required=True, help='Path to CSV file with registrations (one row per participant)')

args=parser.parse_args()

#Input registration file
file=args.input
data=pd.read_csv(file, sep=';')

link='https://www.mn.uio.no/bils/english/events/oslo-bioinfomatics-week/oslo-bioinformatics-workshop-week-2025/'
sender='oslo-bioinfo-workshops@ifi.uio.no'


def applescript_escape(s: str) -> str:
    #AppleScript-formatting
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s


def create_mail_draft(subject, sender, body, bcc_list):
    
    subject_esc = applescript_escape(subject)
    body_esc = applescript_escape(body)
    sender_esc=applescript_escape(sender)

    # AppleScript-linjer for å legge inn BCC-mottakere
    bcc_lines = []
    for email in bcc_list:
        email_esc = applescript_escape(email)
        bcc_lines.append(
            f'        make new bcc recipient at end of bcc recipients of newMessage with properties {{address:"{email_esc}"}}'
        )

    bcc_block = "\n".join(bcc_lines) if bcc_lines else "        -- no recipients"

    applescript = f'''
set subjectText to "{subject_esc}"
set bodyText to "{body_esc}"
set senderAddress to "{sender_esc}"

tell application "Mail"
    set newMessage to make new outgoing message with properties {{subject:subjectText, content:bodyText, sender:senderAddress}}
    tell newMessage
{bcc_block}
        set visible to true
    end tell
    save newMessage
end tell
'''
    sp.run(["osascript", "-e", applescript], check=True)


for title, group in data.groupby("workshop", dropna=False):

    title = title.replace('_',' ')
    subject=f"Your registration to the OBiWoW2025 workshop '{title}'"

    bcc_emails = group['var3'].unique().tolist()

    #Email text
    body = f"""Thank you for registering for the "{title}" workshop.

Please take note of any requirements of the workshop you subscribed to on the workshop website:
{link}

Further information and updates to relevant workshops will be communicated by mail.

Thank you again for your registration. If you have any questions or wish to modify your registration,
please contact us at oslo-bioinfo-workshops@ifi.uio.no.

Regards,
Trainee Committee of BiLS (Bioinformatics in Life Science) at University of Oslo
"""

    print(f"Making draft for {title}: ({len(bcc_emails)} participants)")
    create_mail_draft(subject=subject, sender=sender, body=body, bcc_list=bcc_emails)

print("Done")

    
