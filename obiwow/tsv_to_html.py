import csv
import re
from collections import OrderedDict
from datetime import datetime
from pprint import pprint
from pathlib import Path
import json
import os, sys
import pandas as pd
from mako.template import Template

"""
To do each year: update values for websites and nettskjema.
See below just after 
"""


def room_info(data, dict_room: dict, schedule_columns: dict) -> tuple:
    room_url = None
    room_name = str(data[schedule_columns['room_column']]).strip()
    if str(room_name) != 'nan':
        try:
            room_url = dict_room[room_name]['url']
        except KeyError:
            pass
    else:
        room_name = "No room information available"
    return room_name, room_url


def make_list(raw_string: str) -> tuple[list, bool]:
    split_string = []
    bool_header = False
    # Case if number. is in string in any position
    if re.search(r'\d+\. ', raw_string):
        # Split string before each number
        split_string = re.split(r'(\d+\. )', raw_string)[1:]
        # Only get the even index
        split_string = split_string[1::2]
        split_string = [elm.lstrip(".").strip() for elm in split_string]

    # Case string have with bullet point in any position
    elif re.search(r'•', raw_string):
        split_string = raw_string.split('•')
        # If there is a list header with :
        if ":" in split_string[0] and not (raw_string[0].isdigit() or raw_string[0] == '•' or raw_string[0] == '-'):
            split_string = [split_string[0].rsplit(': ', 1)[0] + ":"] + split_string[1:]
            bool_header = True
        else:
            split_string = split_string[1:]
        split_string = [elm.strip() for elm in split_string]


    # Case string with dash in any position
    elif re.search(r'- ', raw_string):
        split_string = raw_string.split('- ')
        # If there is a list header with :
        if ":" in split_string[0] and not (raw_string[0].isdigit() or raw_string[0] == '•' or raw_string[0] == '-'):
            split_string = [split_string[0].rsplit(': ', 1)[0] + ":"] + split_string[1:]
            bool_header = True
        else:
            split_string = split_string[1:]
        split_string = [elm.strip() for elm in split_string]

    else:
        return [raw_string], bool_header


    return split_string, bool_header


def generate_workshop_body(submission_schedule_df: pd.DataFrame, nettskjema_columns: dict, schedule_columns,
                           yearly: dict, rooms: dict) -> list:
    list_html_section = []

    for index, row in submission_schedule_df.iterrows():
        # Preparing data for workshop body
        workshop_id = row[nettskjema_columns['id_column']]
        workshop_title = row[nettskjema_columns['title_column']].strip()
        workshop_date = datetime.strptime(row[schedule_columns['date_column']], '%d.%m.%y').strftime(
                "%A %d %B %Y") + ' ' + row[schedule_columns['time_column']]
        workshop_ics_path = yearly['ics_folder'] + str(workshop_id) + '.ics'
        room_name, room_url = room_info(row, rooms, schedule_columns)
        workshop_description = row[nettskjema_columns['description_column']]
        list_learning_outcome, bool_header_outcome = make_list(row[nettskjema_columns['outcome_column']])
        workshop_target_audience = row[nettskjema_columns['target_column']]
        list_pre_requisite, bool_header_pre_req = make_list(row[nettskjema_columns['pre_requisite_column']])
        workshop_material = row[nettskjema_columns['material_column']]
        workshop_main_instructor = row[schedule_columns['main_instructor_column']]
        workshop_helper_instructor = str(row[schedule_columns['helper_instructor_column']])
        registration_is_open = yearly['registration_open']
        register_link = yearly['pre_register_link'] + workshop_title.replace(" ", "_") + yearly['post_register_link']


        # Using Mako template to render the workshop body
        workshop_body_template = Template(filename='template/workshop_body_template.html')
        workshop_body_rendered = workshop_body_template.render(
            workshop_id=workshop_id,
            workshop_title=workshop_title,
            workshop_date=workshop_date,
            workshop_ics_path=workshop_ics_path,
            room_map_url=room_url,
            room_name=room_name,
            workshop_description=workshop_description,
            workshop_learning_outcomes=list_learning_outcome,
            workshop_learning_outcomes_header=bool_header_outcome,
            workshop_target_audience=workshop_target_audience,
            workshop_pre_requisites=list_pre_requisite,
            workshop_material=workshop_material,
            workshop_main_instructor=workshop_main_instructor,
            workshop_helper_instructor=workshop_helper_instructor,
            registration_is_open=registration_is_open,
            register_link=register_link,
        )
        list_html_section.append(workshop_body_rendered)

    return list_html_section


def html_list(raw_string):
    line = "<ul>"
    split_string = raw_string.split("- ")

    for elm in split_string:
        line += '<li>'
        line += elm
        line += '</li>'
    line += '</ul>'

    return line


def html_list_outcome(raw_string):
    if ' -' in raw_string:
        split_string = raw_string.split(' -')

        if split_string[0].strip().endswith(":"):
            line = split_string[0].strip()
            line += "<ul>"
            split_string = split_string[1:]
        else:
            line = "<ul>"

        for elm in split_string:
            line += '<li>'
            line += elm
            line += '</li>'
        line += '</ul>'

        return line
    elif "•" in raw_string:
        split_string = raw_string.split('•')

        if split_string[0].strip().endswith(":"):
            line = split_string[0].strip()
            line += "<ul>"
            split_string = split_string[1:]
        else:
            line = "<ul>"

        for elm in split_string:
            if elm != '':
                line += '<li>'
                line += elm.strip()
                line += '</li>'
        line += '</ul>'
        return line

    else:
        return raw_string


def make_room_url(room_name, dict_room_info):
    # print()
    try:
        room_link = '<a rel="noreferrer noopener" target="_blank" href="'
        room_link += dict_room_info[room_name]['url']
        room_link += '">'
        room_link += dict_room_info[room_name]['name']
        room_link += '</a>'
    except KeyError:
        room_link = room_name
    return room_link


def nb_concurrent_workshop(dict_date_schedule):
    count_conc_work = max([len(dict_date_schedule['morning']),
                           len(dict_date_schedule['afternoon'])]) + len(dict_date_schedule['whole_day'])

    return count_conc_work


def make_ics(date, timeslot, location, location_link, event_name, title):
    whole_day = False
    split_timeslot = timeslot.split(" ")
    if len(split_timeslot) > 1:
        whole_day = True

    start_time = timeslot.split("-")[0]
    end_time = timeslot.split("-")[-1]

    datetime_start = datetime.strptime(date + '-' + start_time, '%d.%m.%y-%H:%M')
    datetime_end = datetime.strptime(date + '-' + end_time, '%d.%m.%y-%H:%M')

    ical_start = datetime_start.strftime("%Y%m%d") + "T" + datetime_start.strftime("%H%M%S")
    ical_end = datetime_start.strftime("%Y%m%d") + "T" + datetime_end.strftime("%H%M%S")

    ics_header = "BEGIN:VCALENDAR\n\
VERSION:2.0\n\
PRODID:-//Python 3.10.2//icalendar-5.0.2\n\
CALSCALE:GREGORIAN\n\
BEGIN:VTIMEZONE\n\
TZID:Europe/Oslo\n\
X-LIC-LOCATION:Europe/Oslo\n\
BEGIN:DAYLIGHT\n\
TZNAME:CEST\n\
TZOFFSETFROM:+0100\n\
TZOFFSETTO:+0200\n\
DTSTART:19700329T020000\n\
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU\n\
END:DAYLIGHT\n\
BEGIN:STANDARD\n\
TZNAME:CET\n\
TZOFFSETFROM:+0200\n\
TZOFFSETTO:+0100\n\
DTSTART:19701025T030000\n\
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU\n\
END:STANDARD\n\
END:VTIMEZONE\n\
BEGIN:VEVENT\n"
    ics_header += "DTSTART;TZID=Europe/Oslo:" + ical_start + "\n"
    ics_header += "DTEND;TZID=Europe/Oslo:" + ical_end + "\n"
    ics_header += "SUMMARY:" + event_name + ":\\n" + title + "\n"
    ics_header += "DESCRIPTION:"
    if whole_day:
        ics_header += "Break from 12:00 to 13:00\\n\\n"
    ics_header += "How to get to the room:\\n" + location_link + "\n"
    ics_header += "LOCATION:" + location + "\n"
    ics_header += "END:VEVENT\n\
END:VCALENDAR"

    return ics_header


def read_schedule(schedule_file, delimiter, config):
    """
    Read schedule tsv and creates dicts
    NOTE workshops should have a unique number in the 'Number' column
    with a trailing 0 ('01', '02', ..., '10', '11', ...)
    """
    schedule_id_column = config['schedule_id_column']
    schedule_title_column = config['schedule_title_column']
    schedule_date_column = config['schedule_date_column']
    schedule_room_column = config['schedule_room_column']
    schedule_main_instructor_column = config['schedule_main_instructor_column']
    schedule_helper_instructor_column = config['schedule_helper_instructor_column']
    schedule_max_attendance = config['schedule_max_attendance']
    schedule_time_column = config['schedule_time_column']

    dict_id_name = {}
    dict_schedule_final = {}
    dict_id_timeslot = {}
    dict_title_wsids = {}  # keys: workshop title; values: workshop internal ID

    with open(schedule_file, newline='') as csvfile:
        data = csv.DictReader(csvfile, delimiter=delimiter)
        for row in data:
            if row[schedule_id_column] not in dict_id_name:
                dict_id_name[row[schedule_title_column]] = row[schedule_id_column]

            date = row[schedule_date_column].strip()

            dict_id_timeslot[row[schedule_id_column]] = {}
            dict_id_timeslot[row[schedule_id_column]]['date'] = date.strip()
            dict_id_timeslot[row[schedule_id_column]]['room'] = row[schedule_room_column]
            dict_id_timeslot[row[schedule_id_column]]['main_instructor'] = row[schedule_main_instructor_column]
            dict_id_timeslot[row[schedule_id_column]]['helper'] = row[schedule_helper_instructor_column]
            dict_id_timeslot[row[schedule_id_column]]['title'] = row[schedule_title_column].strip()
            dict_id_timeslot[row[schedule_id_column]]['max_attendance'] = int(row[schedule_max_attendance])

            ws_title = row[schedule_title_column].strip()
            ws_internal_id = row[schedule_id_column]
            dict_title_wsids[ws_title] = ws_internal_id
            # Obtain id of networking event
            if ws_title.startswith("Networking event"):
                networking_event_id = ws_internal_id
            else:
                networking_event_id = None

            if date not in dict_schedule_final:
                dict_schedule_final[date] = {}
                dict_schedule_final[date]['morning'] = []
                dict_schedule_final[date]['afternoon'] = []
                dict_schedule_final[date]['whole_day'] = []

            time = row[schedule_time_column]

            if time == 'full day':
                dict_schedule_final[date]['whole_day'].append(
                    {'id': row[schedule_id_column],
                     'title': row[schedule_title_column]
                     }
                )
                dict_id_timeslot[row[schedule_id_column]]['timeslot'] = '9:00-12:00 13:00-16:00'

            elif time == 'morning':
                dict_schedule_final[date]['morning'].append(
                    {'id': row[schedule_id_column],
                     'title': row[schedule_title_column]
                     }
                )
                dict_id_timeslot[row[schedule_id_column]]['timeslot'] = '9:00-12:00'

            elif time == 'afternoon':
                dict_schedule_final[date]['afternoon'].append(
                    {'id': row[schedule_id_column],
                     'title': row[schedule_title_column]
                     }
                )
                dict_id_timeslot[row[schedule_id_column]]['timeslot'] = '13:00-16:00'

    return dict_schedule_final, dict_id_timeslot, dict_title_wsids, networking_event_id


def get_submission_ID_dict(submission_title_file, delimiter):
    """
    Read in file with nettskjema IDs and workshop titles.
    Return dict with as keys: title, as values: nettskjema ID
    """
    submission_ID_dict = {}
    with open(submission_title_file, newline='') as csvfile:
        data = csv.DictReader(csvfile, delimiter=delimiter)
        for row in data:
            submission_ID_dict[row[title_column]] = row[id_column]
    return submission_ID_dict


def create_schedule_table(dict_schedule_final):
    """
    Create html table from schedule dict
    """
    table_schedule_style = 'border:2px solid black;border-collapse:collapse;'
    table_schedule_header_style = 'border:2px solid black;'

    table_schedule_line_style = 'border-top: 2px solid black;'
    table_schedule_rowname_style = 'border:2px solid black;vertical-align: middle;'
    table_schedule_row_style = 'margin-left:10px;'

    table_header_schedule = '<br><table border="1" style="' + table_schedule_style + '" id="table_sched"><thead><tr style="' + table_schedule_header_style + '"><td><strong>Day</strong></td><td><strong>Morning 9:00-12:00</strong></td><td><strong>Afternoon 13:00-16:00</strong></td></tr></thead>'

    list_line_schedule = []
    for date in dict_schedule_final:
        # catch empty entries
        if not date:
            continue

        nb_conc_workshop = nb_concurrent_workshop(dict_schedule_final[date])

        line_table_schedule = ''
        line_table_schedule += '<tr style="'
        line_table_schedule += table_schedule_line_style
        line_table_schedule += '"><td rowspan="'
        line_table_schedule += str(nb_conc_workshop)
        line_table_schedule += '" style="'
        line_table_schedule += table_schedule_rowname_style
        line_table_schedule += '"><strong>'
        line_table_schedule += datetime.strptime(date, '%d.%m.%y').strftime("%a %d.%m.%y")
        line_table_schedule += '</strong></td>'

        if dict_schedule_final[date]['whole_day']:
            for whole_day in dict_schedule_final[date]['whole_day']:
                line_table_schedule += '<td colspan="2"><p style="'
                line_table_schedule += table_schedule_row_style
                line_table_schedule += '"><a href="#'
                line_table_schedule += whole_day['id']
                line_table_schedule += '">'
                line_table_schedule += whole_day['title']
                line_table_schedule += '</a></p></td></tr><tr>'

        for i in range(nb_conc_workshop - len(dict_schedule_final[date]['whole_day'])):
            line_table_schedule += '<td><p style="'
            line_table_schedule += table_schedule_row_style
            line_table_schedule += '">'
            try:
                morning_dict = dict_schedule_final[date]['morning'][i]
                line_table_schedule += '<a href="#'
                line_table_schedule += morning_dict['id']
                line_table_schedule += '">'
                line_table_schedule += morning_dict['title']
                line_table_schedule += '</a>'
            except IndexError:
                pass
            line_table_schedule += '</p></td><td>'

            try:
                afternoon_dict = dict_schedule_final[date]['afternoon'][i]
                line_table_schedule += '<a href="#'
                line_table_schedule += afternoon_dict['id']
                line_table_schedule += '">'
                line_table_schedule += afternoon_dict['title']
                line_table_schedule += '</a>'
            except IndexError:
                pass
            line_table_schedule += '</p></td></tr><tr>'
        list_line_schedule.append(line_table_schedule.rsplit('<tr>', 1)[0])
    return table_header_schedule, list_line_schedule


def adjust_event(list_line_schedule, event_id, event_url):
    """
    Some events have their own url instead of a desription on the webpage.
    Replace the internal html tag with this url.
    """
    new_list_line_schedule = []
    for row in list_line_schedule:
        if "Networking event" in row:
            row = row.replace(f'<a href="#{event_id}">', f'<a href="{event_url}">')
            print("Succesfully added link to Networking event to schedule.")
        new_list_line_schedule.append(row)
    return new_list_line_schedule


def read_workshops(workshop_description_tsv, dict_subm_title, dict_ids, delimiter, dict_id_timeslot, dict_yearly,
                   dict_room, registration_is_open=True):
    """
    Parse workshop description nettkjema tsv dump
    into a list of html-formatted sections
    Create dict of nettskjema ID and internal workshop ID
    """
    with open(workshop_description_tsv, newline='') as csvfile:
        data = csv.DictReader(csvfile, delimiter=delimiter)
        list_html_section = []
        list_table = []

        for row in data:

            # match title, nettskjema ID and workshop ID

            ws_title = row['Title of the workshop'].strip()
            # check whether workshop title is scheduled
            if ws_title in dict_subm_title:
                nettskjema_ID = dict_subm_title[ws_title]
            elif ws_title.startswith("Networking event"):
                # Networking event will not have description below the table
                continue
            else:
                # print(f"Submitted proposal '{ws_title}' is not in file '{path_subm_title}', ignoring...\n")
                continue

            # check whether title is in dict with titles and internal workshop IDs
            if ws_title in dict_ids:
                workshop_id = dict_ids[ws_title]
            else:
                sys.exit(f"Fatal: found unknown workshop title, stemming from '{path_schedule}' file: '{ws_title}'")

            # in case of multiple submissions for the same workshop,
            # take the one from the path_subm_title file (submission_title.tsv)
            if str(nettskjema_ID) != str(row['$submission_id']):
                # this is not the correct one, skip
                print('Nope', nettskjema_ID, row['$submission_id'], type(nettskjema_ID), type(row['$submission_id']),
                      nettskjema_ID == row['$submission_id'])
                continue

            # workshop_id = str(workshop_id)

            html_section = '<hr class="double"><div id="'
            html_section += str(workshop_id)
            html_section += '"><h2>'
            html_section += row['Title of the workshop'].strip()
            html_section += '</h2><p><strong><u>Date</u>: '
            html_section += datetime.strptime(dict_id_timeslot[workshop_id]['Date'], '%d.%m.%y').strftime(
                "%A %d %B %Y") + ' ' + dict_id_timeslot[workshop_id]['Time']
            html_section += '</strong> '
            html_section += '<a rel="noreferrer noopener" target="_blank" href="' + dict_yearly['ics_folder'] + str(
                workshop_id) + '.ics">Add to calendar</a>'
            html_section += '</p><strong><u>Room</u>:</strong> '
            html_section += str(make_room_url(dict_id_timeslot[workshop_id]['Room in Ole Johan Dalshus'], dict_room))
            if registration_is_open:
                html_section += '<p><a rel="noreferrer noopener" target="_blank" href="'
                html_section += pre_register_link + row['Title of the workshop'].strip().replace(" ",
                                                                                                 "_") + post_register_link
                html_section += '">Register here</a></p><p></p><h3>Description</h3><p align="justify">'
            html_section += row['A short description of your workshop (max 250 words)']
            html_section += '</p><div style="background-color:#b6efed;width:90%;border-radius: 15px;padding: 10px;margin-left: auto;margin-right: auto;"><p><h4>Learning outcomes</h4>'
            html_section += html_list_outcome(row[
                                                  'A brief statement on the learning outcomes from the workshop, to be used on the website for the event.'])
            html_section += '</p><br></div><h3>Target audience</h3><p>'
            html_section += row['What is the target audience for your workshop?']
            html_section += '</p></div><h3>Pre-requisites</h3><p>'
            html_section += html_list(row['What are the prerequisites for attending the workshop?'])
            html_section += '</p><h3>Equipment to bring</h3><p>'
            html_section += row['Please indicate what you expect your audience need to bring to the workshop']
            html_section += '</p><p><strong>Instructor(s):<br></strong>'
            html_section += str(dict_id_timeslot[workshop_id]['Instructor 1']) + ' (main)<br>'
            html_section += str(dict_id_timeslot[workshop_id]['Instructor 2'])

            html_section += '</p><a href="#table_sched">Go back</a></div>'

            list_html_section.append(html_section)

    return list_html_section


def write_html(table_header_schedule, list_line_schedule, list_html_section, footer_file):
    """
    Collect all html information and write to file
    """
    html_all = '<h2>Agenda</h2>'

    # add table
    html_all += table_header_schedule

    for line in list_line_schedule:
        html_all += line + "\n"

    html_all += '</table><br>'

    # add content from footer.html
    with open(footer_file, "r") as fh:
        footer_content = fh.readlines()
    html_all += "\n" + "\n".join(footer_content) + "\n"

    # add workshop descriptions
    for section in list_html_section:
        html_all += section + "\n"

        # write the final html
    file = open(outfile, 'w')
    file.write(html_all)
    file.close()


def write_ical(outdir_ics, dict_id_timeslot, event_name):
    """
    Write individual ics files for each workshop
    """
    # Create ical folder if necessary
    Path(outdir_ics).mkdir(parents=True, exist_ok=True)
    # Remove any existing .ics files
    for ics_file in Path(outdir_ics).glob('*.ics'):
        if ics_file.is_file():
            ics_file.unlink()

    for id in dict_id_timeslot:
        # catch empty entries
        if not id:
            continue
        ics_text = make_ics(dict_id_timeslot[id]['date'],
                            dict_id_timeslot[id]['timeslot'],
                            dict_id_timeslot[id]['room'],
                            dict_room[dict_id_timeslot[id]['room']]['url'],
                            dict_id_timeslot[id]['title'],
                            event_name,
                            )
        outpath_ics = os.path.join(outdir_ics, id + ".ics")
        with open(outpath_ics, 'w') as file:
            file.write(ics_text)

# if __name__ == '__main__':
# """
# Update each year
# """
#
# # set to False one registration is closed
# # generate workshop_content again to remove registration links
# registration_open = False
#
# event_name = 'Oslo Bioinformatics Workshop Week 2023'
# pre_register_link = "https://nettskjema.no/a/375340?CBworkshop="
# post_register_link = "&LCKworkshop=true"
#
# ics_folder = "https://www.mn.uio.no/sbi/english/events/oslo-bioinformatics-workshop-week-2023/ics_files/"
#
# networking_event_url = "https://www.mn.uio.no/sbi/english/events/oslo-bioinformatics-workshop-week-2023/networking-event-panel-discussion"
# """
# Update for each year if necessary
# """
# path_tsv = "survey_results.csv"  # csv dump of nettskjema with proposals
# path_subm_title = "submission_title.csv"  # extracted from survey_results.csv,  with only nettskjema ID and title, edited
# path_schedule = "schedule.tsv"  # tsv dump of Google sheet with schedule
# footer = "footer.html"  # html file with text to be added below the schedule
# outfile = "workshop_content.html"
# outdir_ics = "ical"
# subm_delim = ";"
#
# """
# Update when nettskjema a questions have changed.
# """
# id_column = '$submission_id'
# title_column = 'Title of the workshop'
# form_column = 'form_link'
# description_column = 'A short description of your workshop (max 250 words)'
# outcome_column = 'A brief statement on the learning outcomes from the workshop, to be used on the website for the event.'
# pre_requisit = 'What are the prerequisites for attending the workshop?'
# instructor_column = 'Your name (first name and surname)?'
# email_column = 'What is your e-mail address?'
# duration_column = 'Length of the workshop (e.g., 2 hours, half a day or a whole day)'
# material_column = 'Please indicate what you expect your audience need to bring to the workshop'
# target_column = 'What is the target audience for your workshop?'
#
# """
# Update when Google sheet with schedule column names have changed.
# """
# schedule_date_column = "Date"
# schedule_time_column = "Time"
# schedule_title_column = "Workshop name"
# schedule_id_column = "Number"
# schedule_room_column = 'Room in Ole Johan Dalshus'
# schedule_main_instructor_column = 'Instructor 1'
# schedule_helper_instructor_column = 'Instructor 2'
# schedule_max_attendance = 'Max capacity'
#
# """
# Update when rooms (details) have changed
# IMPORTANT keep the room number (e.g. Sed (room 1454)'),
# as this information will be part of the calender entry file.
# """
# dict_room = {
#     'Sed (room 1454)':
#         {
#             'name': 'Sed (room 1454) in Ole-Johan Dahls hus (OJD)',
#             'url': 'https://use.mazemap.com/#v=1&config=uio&center=10.718810,59.943890&zoom=18&sharepoitype=poi&sharepoi=1000987466&zlevel=1&campusid=799',
#         },
#     'Perl (room 2453)':
#         {
#             'name': 'Perl (room 2453) in Ole-Johan Dahls hus (OJD)',
#             'url': 'https://use.mazemap.com/#v=1&config=uio&zlevel=2&center=10.718834,59.943903&zoom=18&sharepoitype=poi&sharepoi=1000987629&campusid=801',
#         },
#     'Python (room 2269)':
#         {
#             'name': 'Python (room 2269) in Ole-Johan Dahls hus (OJD)',
#             'url': 'https://use.mazemap.com/#v=1&config=uio&zlevel=2&center=10.719242,59.944188&zoom=18&sharepoitype=poi&sharepoi=1000987605&campusid=799',
#         },
#     'Room 3205 IBV, Hox(Computer lab)':
#         {
#             'name': 'Hox (Computer lab, room 3205) Kristine Bonnevieshus',
#             'url': 'https://use.mazemap.com/#v=1&config=uio&zlevel=3&center=10.723863,59.938264&zoom=18&sharepoitype=poi&sharepoi=1000974921&campusid=799',
#         },
#     'Prolog (room 2465)':
#         {
#             'name': 'Prolog (room 2465) in Ole-Johan Dahls hus (OJD)',
#             'url': 'https://use.mazemap.com/#v=1&config=uio&zlevel=2&center=10.719105,59.944047&zoom=18&sharepoitype=poi&sharepoi=1000987623&campusid=799'
#         },
#     'Postscript (room 2458)':
#         {
#             'name': 'Postscript (room 2458) in Ole-Johan Dahls hus (OJD)',
#             'url': 'https://use.mazemap.com/#v=1&config=uio&center=10.718931,59.943959&zoom=18&sharepoitype=poi&sharepoi=1000987608&zlevel=2&campusid=799'
#         },
#     'Auditorium Smalltalk':
#         {
#             'name': 'Auditorium Smalltalk, Ole Johan Dalshus (OJD)',
#             'url': 'https://use.mazemap.com/?campusid=799&sharepoitype=identifier&sharepoi=GA06-1416&config=uio'
#         }
# }

################################
#     Here the work starts     #
################################

# # obtain nettskjema submission ID and title dict
# dict_subm_title = get_submission_ID_dict(path_subm_title, subm_delim)
#
# # parse schedule into dicts
# dict_schedule_final, dict_id_timeslot, dict_ids, networking_event_id = read_schedule(path_schedule, delimiter="\t")
#
# # write dict_id_timeslot to file for other scripts to use
# with open("schedule.json", "w") as schedule_out:
#     schedule_out.write(json.dumps(dict_id_timeslot))
#
# # read and parse workshop descriptions
# list_html_section = read_workshops(path_tsv, dict_subm_title, dict_ids, subm_delim, registration_open)
#
# # create schedule table html
# table_header_schedule, list_line_schedule = create_schedule_table(dict_schedule_final)
#
# # adjust for Networking event: should link to its own webpage
# list_line_schedule = adjust_event(list_line_schedule, networking_event_id, networking_event_url)
#
# # collect all output in html format
# write_html(table_header_schedule, list_line_schedule, list_html_section, footer)
#
# # write ical files
# write_ical(outdir_ics, dict_id_timeslot, event_name)
#
# print("Success! Output files written to disk.")
# print(f"Use '{outfile}' as raw html for the workshop website.")
# print(f"Copy '*.ics' files in the '{outdir_ics}' folder so that they are in {ics_folder}.")
