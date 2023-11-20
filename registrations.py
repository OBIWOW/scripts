import sys
import json
import subprocess
from pathlib import Path
from pprint import pprint

def do_cmd(cmd, dryrun = False):
    """
    Run the command
    """
    if dryrun:
        print(f"Would be running: {cmd}")
        return
    else:
        print(f"Will run: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        #sys.exit(result.stdout)
        return result.stdout
    else:
        # empty result, maybe there is no internet connection?
        msg = "API call unsucessful, empty result returned.\n"
        msg += "This could be the result of the lack of an internet connection."
        sys.exit(msg)

# fungerer:
API_token = 'hu6vtdsdu3er9a7cur5utsucimef8d019rmseud5egpiik0qma5qt87m3sjstn4s3tcbghtlfgeer81tnm7hqi9k6tvov78bpd5fiqtfknejhi277ctab37jfvaf9pl03bdn'
# fungerer ikke:
#API_token = 'yw813079kd3uj2h5obavh6uhkr92egel5hortm8q264pmteb4ibtsdi5dcgr1fvknpphuitvoo9du4tdu762o9ovrvi3gbnfv99enb0v81mlll17a9cmosqvrng8qckrfpj'


nettskjema_ID = '375340'
# fields in the json output
workshop_title_questionId = 6472526

cmd = f"""
curl 'https://nettskjema.no/api/v2/forms/{nettskjema_ID}/submissions' \
    -i -X GET  \
    -H 'Authorization: Bearer {API_token}'
"""    

submissions = do_cmd(cmd, dryrun = False)

# submissions are in the last line
submissions = submissions.split("\n")[-1]

# test for success
if submissions.startswith('{"statusCode":'):
    print("API call not successful:")
    pprint(json.loads(submissions))
    sys.exit()

# convert to json
submissions = json.loads(submissions)

workshops = {}
emails = {}

for submission in submissions:
    email_address = submission['respondentEmail']
    emails[email_address] = emails.get(email_address, 0) + 1
    answers = submission['answers']
    for answer in answers:
        if answer['questionId'] == workshop_title_questionId:
            workshop_title = answer['textAnswer']
            workshops[workshop_title] = workshops.get(workshop_title, 0) + 1


print(f"Total unique email addresses:\t{len(emails)}")

# sort by number of registrations
sorted_email_by_registrations = dict(sorted(emails.items(), key=lambda x:x[1], reverse = True))

print("Top 5 registered workshop per email address")
for email in {k: sorted_email_by_registrations[k] for k in list(sorted_email_by_registrations)[:5]}:
    print(f"{email}\t{sorted_email_by_registrations[email]}")
print()

# sort by number of registrations
sorted_ws_by_registrations = dict(sorted(workshops.items(), key=lambda x:x[1]))

for ws_title in sorted_ws_by_registrations:
    print(f"{ws_title}\t{sorted_ws_by_registrations[ws_title]}")

print(f"Total registrations:\t{sum(workshops.values())}")
