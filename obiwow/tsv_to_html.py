import csv
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from mako.template import Template


def room_info(data, dict_room: dict, schedule_columns: dict) -> tuple:
    """
    Get room information from schedule data.
    If room information is not available, return a default message.

    Args:
        data (pd.Series): A row of the schedule data.
        dict_room (dict): Dictionary containing room information.
        schedule_columns (dict): Dictionary mapping column names for the schedule data.

    Returns:
        tuple: A tuple containing the room name and the room URL.
    """
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
    """
    Split string into list of strings based on bullet points, dashes, or numbers.
    If the string starts with a header, return the header as a separate string.

    Args:
        raw_string (str): The string to split.

    Returns:
        tuple[list, bool]: A list of strings and a boolean indicating if the first string is a header.
    """
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
    """
    Generates the HTML body for each workshop using the Mako template.

    Args:
        submission_schedule_df (pd.DataFrame): DataFrame containing the workshop schedule.
        nettskjema_columns (dict): Dictionary mapping column names for the nettskjema data.
        schedule_columns (dict): Dictionary mapping column names for the schedule data.
        yearly (dict): Dictionary containing yearly configuration values.
        rooms (dict): Dictionary containing room information.

    Returns:
        list: A list of HTML sections for each workshop.
    """

    list_html_section = []

    project_root = Path(__file__).resolve().parent.parent
    template_path = os.path.join(project_root, 'template', 'workshop_body_template.html')
    workshop_body_template = Template(filename=template_path)

    for index, row in submission_schedule_df.iterrows():

        networking_event = row[schedule_columns['networking_event_column']]
        # Pass if networking event
        if networking_event:
            continue

        # Preparing data for workshop body
        workshop_number = row[schedule_columns['id_column']]
        workshop_title = row[nettskjema_columns['title_column']].strip()
        workshop_date = datetime.strptime(row[schedule_columns['date_column']], '%d.%m.%y').strftime(
            "%A %d %B %Y")
        workshop_time = row[schedule_columns['start_time_column']] + '-' + row[schedule_columns['end_time_column']]
        if workshop_time == '9:00-16:00':
            workshop_time = '9:00-12:00 13:00-16:00'
        workshop_ics_path = yearly['ics_folder'] + str(workshop_number) + '.ics'
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
        workshop_body_rendered = workshop_body_template.render(
            workshop_number=workshop_number,
            workshop_title=workshop_title,
            workshop_date=workshop_date,
            workshop_time=workshop_time,
            workshop_ics_path=workshop_ics_path,
            room_map_url=room_url,
            room_name=room_name,
            workshop_description=workshop_description,
            workshop_learning_outcomes=list_learning_outcome,
            workshop_learning_outcomes_header=bool_header_outcome,
            workshop_target_audience=workshop_target_audience,
            workshop_pre_requisites=list_pre_requisite,
            workshop_pre_requisites_header=bool_header_pre_req,
            workshop_material=workshop_material,
            workshop_main_instructor=workshop_main_instructor,
            workshop_helper_instructor=workshop_helper_instructor,
            registration_is_open=registration_is_open,
            register_link=register_link,
        )
        list_html_section.append(workshop_body_rendered)

    return list_html_section


def generate_schedule_table(schedule_df: pd.DataFrame, schedule_columns: dict, yearly: dict) -> str:
    list_html_section = []
    # Convert 'Date' column to datetime objects
    schedule_df['Date'] = pd.to_datetime(schedule_df['Date'], format='%d.%m.%y')

    # Sort the DataFrame by the 'Date' column
    df_schedule = schedule_df.sort_values(by='Date')

    project_root = Path(__file__).resolve().parent.parent
    template_path = os.path.join(project_root, 'template', 'schedule_table_template.html')

    schedule_table_template = Template(filename=template_path)
    schedule_table_rendered = schedule_table_template.render(
        df_schedule=schedule_df,
        schedule_columns=schedule_columns,
        network_url=yearly['networking_event_url'],
    )
    return schedule_table_rendered


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


def generate_full_html_page(schedule_table_html: str, workshop_body_html: list, yearly: dict) -> str:
    """
    Generate the full HTML page using the Mako template.

    Args:
        schedule_table_html (str): The HTML for the schedule table.
        workshop_body_html (str): The HTML for the workshop body.
        yearly (dict): Dictionary containing yearly configuration values.

    Returns:
        str: The full HTML page.
    """
    # Make footer
    project_root = Path(__file__).resolve().parent.parent
    header_template_path = os.path.join(project_root, 'template', 'header_template.html')
    header_page_template = Template(filename=header_template_path)

    header_page_rendered = header_page_template.render(
        page_title=yearly['event_name'],
    )

    footer_template_path = os.path.join(project_root, 'template', 'footer_template.html')
    footer_page_template = Template(filename=footer_template_path)
    footer_page_rendered = footer_page_template.render()
    full_page_rendered = ''
    try:
        full_page_rendered += header_page_rendered
        full_page_rendered += schedule_table_html
        full_page_rendered += "\n".join(workshop_body_html)
        full_page_rendered += footer_page_rendered
    except Exception as e:
        print(e)

    return full_page_rendered
