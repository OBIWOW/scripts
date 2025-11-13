import csv
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

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
    # Use a single regex pattern to match numbers, bullet points, or dashes
    pattern = r'(\d+- |\d+\. |•|- |\*)'
    if re.search(pattern, raw_string):
        split_string = re.split(pattern, raw_string)
        split_string = [elm.strip() for elm in split_string if not re.match(pattern, elm)]
        # Check for header
        if ":" in split_string[0] and not (raw_string[0].isdigit() or raw_string[0] in ['•', '-', '*']):
            split_string = [split_string[0].rsplit(': ', 1)[0]] + split_string[1:]
            bool_header = True
    else:
        return [raw_string], bool_header

    return list(filter(None, split_string)), bool_header


def get_clean_value(row: pd.Series, column_name: str, default: str = "") -> str:
    """
    Return a cleaned string value from a pandas Series for the given column name.

    Args:
        row (pd.Series): The current row being processed.
        column_name (str): The column to retrieve.
        default (str): Fallback value if the column is missing or NaN.

    Returns:
        str: The cleaned string value.
    """
    value = row.get(column_name, default)
    if pd.isna(value) or value is None:
        return default
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def parse_workshop_date(date_str: str) -> Optional[datetime]:
    """
    Parse a workshop date string using multiple possible formats.

    Args:
        date_str (str): The date string to parse.

    Returns:
        Optional[datetime]: Parsed datetime object if successful, otherwise None.
    """
    normalized = str(date_str).strip()
    if not normalized:
        return None

    candidate_values: list[str] = []
    for separator in (' to ', '-', '–', '—'):
        if separator in normalized:
            candidate = normalized.split(separator, 1)[0].strip()
            if candidate:
                candidate_values.append(candidate)
    candidate_values.append(normalized)

    seen: set[str] = set()
    date_formats = (
        '%d.%m.%y',
        '%d.%m.%Y',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%Y-%m-%d',
    )

    for candidate in candidate_values:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        for date_format in date_formats:
            try:
                return datetime.strptime(candidate, date_format)
            except ValueError:
                continue

        try:
            parsed = pd.to_datetime(candidate, dayfirst=True, errors='raise')
            return parsed.to_pydatetime()
        except Exception:
            continue

    print(f"WARNING: Unable to parse workshop date '{date_str}'. Using raw value.")
    return None


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

    seen_workshops = set()

    for index, row in submission_schedule_df.iterrows():

        networking_event = row[schedule_columns['networking_event_column']]
        # Pass if networking event
        if networking_event:
            continue

        # Check for duplicate workshop (by title + description)
        this_title = get_clean_value(row, nettskjema_columns['title_column'], default="")
        this_desc = get_clean_value(row, nettskjema_columns['description_column'], default="")
        key = (this_title.strip().lower(), this_desc.strip().lower())
        if key in seen_workshops:
            continue
        seen_workshops.add(key)

        # Preparing data for workshop body
        is_multiday = False  # Initialize flag for every row
        workshop_number = get_clean_value(row, schedule_columns['id_column'], default=str(index + 1))
        schedule_title = get_clean_value(row, schedule_columns['title_column'],
                                         default=f"Workshop {workshop_number}")
        workshop_title = get_clean_value(row, nettskjema_columns['title_column'],
                                         default=schedule_title or f"Workshop {workshop_number}")
        workshop_date_str = get_clean_value(row, schedule_columns['date_column'])
        parsed_date = parse_workshop_date(workshop_date_str)
        if parsed_date:
            workshop_date = parsed_date.strftime("%A %d %B %Y")
        else:
            workshop_date = workshop_date_str
        start_time = get_clean_value(row, schedule_columns['start_time_column'])
        end_time = get_clean_value(row, schedule_columns['end_time_column'])
        if start_time and end_time:
            workshop_time = f"{start_time}-{end_time}"
        else:
            workshop_time = start_time or end_time or ""
        # For multi-day range, do NOT add block times to the date string
        if is_multiday:
            workshop_time = ""  # do not append any block time
        elif workshop_time == '9:00-16:00':
            workshop_time = '9:00-12:00 13:00-16:00'
        workshop_ics_path = yearly['ics_folder'] + str(workshop_number) + '.ics'
        room_name, room_url = room_info(row, rooms, schedule_columns)
        workshop_description = get_clean_value(row, nettskjema_columns['description_column'])

        # --- Multi-day workshop date span fix ---
        is_multiday = (
            " - Day 1" in schedule_title and not row.get('multi_day_final', True)
        )
        if is_multiday:
            # Grab the base title
            base_title = schedule_title.rsplit(" - Day", 1)[0].strip()
            # Filter all rows in submission_schedule_df for matching base title
            candidates = submission_schedule_df[
                submission_schedule_df[schedule_columns['title_column']].str.startswith(base_title)
            ]
            # Find the last day (multi_day_final True)
            last_day_row = candidates[candidates['multi_day_final'] == True]
            if not last_day_row.empty:
                # Use the first day info from current row
                first_date = parsed_date.strftime("%A %d %B %Y") if parsed_date else workshop_date_str
                first_time = start_time
                # Use the last day info
                last_row = last_day_row.iloc[0]
                last_date_raw = get_clean_value(last_row, schedule_columns['date_column'])
                last_date_obj = parse_workshop_date(last_date_raw)
                last_date = last_date_obj.strftime("%A %d %B %Y") if last_date_obj else last_date_raw
                last_end_time = get_clean_value(last_row, schedule_columns['end_time_column'])
                workshop_date = f"{first_date} {first_time} - {last_date} {last_end_time}"
            else:
                # Fallback to single-day logic
                workshop_date = workshop_date if workshop_date else workshop_date_str
        # --- End multi-day fix ---

        outcome_value = get_clean_value(row, nettskjema_columns['outcome_column'])
        if outcome_value:
            list_learning_outcome, bool_header_outcome = make_list(outcome_value)
        else:
            list_learning_outcome, bool_header_outcome = [], False
        workshop_target_audience = get_clean_value(row, nettskjema_columns['target_column'])
        pre_req_value = get_clean_value(row, nettskjema_columns['pre_requisite_column'])
        if pre_req_value:
            list_pre_requisite, bool_header_pre_req = make_list(pre_req_value)
        else:
            list_pre_requisite, bool_header_pre_req = [], False
        workshop_material = get_clean_value(row, nettskjema_columns['material_column'])
        workshop_main_instructor = get_clean_value(row, schedule_columns['main_instructor_column'])
        workshop_helper_instructor = get_clean_value(row, schedule_columns['helper_instructor_column'])
        registration_is_open = yearly['registration_open']
        register_title_slug = (workshop_title or schedule_title or f"workshop_{workshop_number}").replace(" ", "_")
        register_link = yearly['pre_register_link'] + register_title_slug + yearly['post_register_link']

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
    schedule_df = schedule_df.copy()

    parsed_dates = schedule_df[schedule_columns['date_column']].apply(parse_workshop_date)
    sort_dates = [
        value if isinstance(value, datetime) else datetime.max
        for value in parsed_dates
    ]

    sorted_schedule_df = (
        schedule_df
        .assign(_parsed_date=parsed_dates, _sort_date=sort_dates)
        .sort_values(by='_sort_date')
        .drop(columns=['_sort_date'])
    )
    parsed_mask = sorted_schedule_df['_parsed_date'].notna()
    sorted_schedule_df.loc[parsed_mask, schedule_columns['date_column']] = sorted_schedule_df.loc[
        parsed_mask, '_parsed_date'
    ]
    sorted_schedule_df = sorted_schedule_df.drop(columns=['_parsed_date'])

    project_root = Path(__file__).resolve().parent.parent
    template_path = os.path.join(project_root, 'template', 'schedule_table_template.html')

    schedule_table_template = Template(filename=template_path)
    schedule_table_rendered = schedule_table_template.render(
        df_schedule=sorted_schedule_df,
        schedule_columns=schedule_columns,
        network_url=yearly['networking_event_url'],
    )
    return schedule_table_rendered

#
# def read_schedule(schedule_file, delimiter, config):
#     """
#     Read schedule tsv and creates dicts
#     NOTE workshops should have a unique number in the 'Number' column
#     with a trailing 0 ('01', '02', ..., '10', '11', ...)
#     """
#     schedule_id_column = config['schedule_id_column']
#     schedule_title_column = config['schedule_title_column']
#     schedule_date_column = config['schedule_date_column']
#     schedule_room_column = config['schedule_room_column']
#     schedule_main_instructor_column = config['schedule_main_instructor_column']
#     schedule_helper_instructor_column = config['schedule_helper_instructor_column']
#     schedule_max_attendance = config['schedule_max_attendance']
#     schedule_time_column = config['schedule_time_column']
#
#     dict_id_name = {}
#     dict_schedule_final = {}
#     dict_id_timeslot = {}
#     dict_title_wsids = {}  # keys: workshop title; values: workshop internal ID
#
#     with open(schedule_file, newline='') as csvfile:
#         data = csv.DictReader(csvfile, delimiter=delimiter)
#         for row in data:
#             if row[schedule_id_column] not in dict_id_name:
#                 dict_id_name[row[schedule_title_column]] = row[schedule_id_column]
#
#             date = row[schedule_date_column].strip()
#
#             dict_id_timeslot[row[schedule_id_column]] = {}
#             dict_id_timeslot[row[schedule_id_column]]['date'] = date.strip()
#             dict_id_timeslot[row[schedule_id_column]]['room'] = row[schedule_room_column]
#             dict_id_timeslot[row[schedule_id_column]]['main_instructor'] = row[schedule_main_instructor_column]
#             dict_id_timeslot[row[schedule_id_column]]['helper'] = row[schedule_helper_instructor_column]
#             dict_id_timeslot[row[schedule_id_column]]['title'] = row[schedule_title_column].strip()
#             dict_id_timeslot[row[schedule_id_column]]['max_attendance'] = int(row[schedule_max_attendance])
#
#             ws_title = row[schedule_title_column].strip()
#             ws_internal_id = row[schedule_id_column]
#             dict_title_wsids[ws_title] = ws_internal_id
#             # Obtain id of networking event
#             if ws_title.startswith("Networking event"):
#                 networking_event_id = ws_internal_id
#             else:
#                 networking_event_id = None
#
#             if date not in dict_schedule_final:
#                 dict_schedule_final[date] = {}
#                 dict_schedule_final[date]['morning'] = []
#                 dict_schedule_final[date]['afternoon'] = []
#                 dict_schedule_final[date]['whole_day'] = []
#
#             time = row[schedule_time_column]
#
#             if time == 'full day':
#                 dict_schedule_final[date]['whole_day'].append(
#                     {'id': row[schedule_id_column],
#                      'title': row[schedule_title_column]
#                      }
#                 )
#                 dict_id_timeslot[row[schedule_id_column]]['timeslot'] = '9:00-12:00 13:00-16:00'
#
#             elif time == 'morning':
#                 dict_schedule_final[date]['morning'].append(
#                     {'id': row[schedule_id_column],
#                      'title': row[schedule_title_column]
#                      }
#                 )
#                 dict_id_timeslot[row[schedule_id_column]]['timeslot'] = '9:00-12:00'
#
#             elif time == 'afternoon':
#                 dict_schedule_final[date]['afternoon'].append(
#                     {'id': row[schedule_id_column],
#                      'title': row[schedule_title_column]
#                      }
#                 )
#                 dict_id_timeslot[row[schedule_id_column]]['timeslot'] = '13:00-16:00'
#
#     return dict_schedule_final, dict_id_timeslot, dict_title_wsids, networking_event_id


def generate_full_html_page(schedule_table_html: str, workshop_body_html: list, yearly: dict, paths: dict) -> str:
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

    path_schedule_footer = paths['input']['footer']['file_path']
    with open(path_schedule_footer, 'r') as f:
        footer_schedule_rendered = f.read()

    footer_template_path = os.path.join(project_root, 'template', 'footer_template.html')
    footer_page_template = Template(filename=footer_template_path)
    footer_page_rendered = footer_page_template.render()
    full_page_rendered = ''
    try:
        full_page_rendered += header_page_rendered
        full_page_rendered += footer_schedule_rendered
        full_page_rendered += schedule_table_html
        full_page_rendered += "\n".join(workshop_body_html)
        full_page_rendered += footer_page_rendered
    except Exception as e:
        print(e)

    return full_page_rendered
