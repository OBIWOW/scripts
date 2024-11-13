from __future__ import annotations

import os
import re
from datetime import timedelta, datetime
from pathlib import Path
from typing import Tuple
from mako.template import Template

import yaml
import pandas as pd



def add_duration_to_time(start_time_str, duration_str):
    duration_str = duration_str.strip()
    # Parse the start time
    start_time = datetime.strptime(start_time_str, '%H:%M')

    # Parse the duration
    duration_match = re.match(r'(\d+)\s*(min|hours?)', duration_str)
    if not duration_match:
        print(f'Invalid duration format {duration_str}')
        # return 12:00 as default if start time is 9:00
        if start_time_str == '9:00':
            return '12:00'
        # return 16:00 as default if start time is 13:00
        elif start_time_str == '13:00':
            return '16:00'

    duration_value = int(duration_match.group(1))
    duration_unit = duration_match.group(2)

    # Calculate the timedelta
    if 'hour' in duration_unit:
        duration = timedelta(hours=duration_value)
    elif 'min' in duration_unit:
        duration = timedelta(minutes=duration_value)
    else:
        raise ValueError("Invalid duration unit")

    # Add the duration to the start time
    end_time = start_time + duration

    return end_time.strftime('%H:%M')


def get_start_end_time(data, schedule_columns: dict) -> tuple[str | None, str | None]:
    workshop_date = datetime.strptime(data[schedule_columns['date_column']], '%d.%m.%y').strftime("%A %d %B %Y")
    workshop_start_time = None
    workshop_end_time = None
    if data[schedule_columns['duration_column']] == 'all day':
        workshop_start_time = '9:00'
        workshop_end_time = '16:00'
    elif data[schedule_columns['time_column']] == 'morning':
        # If no duration is given, default to 9:00-12:00
        if str(data[schedule_columns['duration_column']]) == 'nan':
            workshop_start_time = '9:00'
            workshop_end_time = '12:00'
        elif str(data[schedule_columns['duration_column']]) == 'half a day':
            workshop_start_time = '9:00'
            workshop_end_time = '12:00'
        else:
            workshop_start_time = '9:00'
            workshop_end_time = add_duration_to_time('9:00', str(data[schedule_columns['duration_column']]))
    elif data[schedule_columns['time_column']] == 'afternoon':
        # If no duration is given, default to 13:00-16:00
        if str(data[schedule_columns['duration_column']]) == 'nan':
            workshop_start_time = '13:00'
            workshop_end_time = '16:00'
        elif str(data[schedule_columns['duration_column']]) == 'half a day':
            workshop_start_time = '13:00'
            workshop_end_time = '16:00'
        else:
            workshop_start_time = '13:00'
            workshop_end_time = add_duration_to_time('13:00', str(data[schedule_columns['duration_column']]))

    return workshop_start_time, workshop_end_time


def add_start_end_time_to_schedule(schedule_df: pd.DataFrame, schedule_columns: dict) -> pd.DataFrame:
    schedule_df[schedule_columns['start_time_column']] = None
    schedule_df[schedule_columns['end_time_column']] = None
    for index, row in schedule_df.iterrows():
        start_time, end_time = get_start_end_time(row, schedule_columns)
        schedule_df.at[index, schedule_columns['start_time_column']] = start_time
        schedule_df.at[index, schedule_columns['end_time_column']] = end_time

    return schedule_df


def parse_yaml(path_conf: str) -> dict | None:
    try:
        with open(path_conf, 'r') as file:
            try:
                dict_conf = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print(f"Error in configuration file {path_conf}: {exc}")
                dict_conf = None
    except FileNotFoundError:
        print(f"Configuration file {path_conf} not found.")
        dict_conf = None

    return dict_conf


def parse_csv_to_pandas(csv_content: str, delimiter: str) -> pd.Dataframe | None:
    try:
        df = pd.read_csv(csv_content, delimiter=delimiter, header=0)
    except FileNotFoundError:
        print(f"File {csv_content} not found.")
        df = None
    return df


def get_submission_ID_dict(submission_dataframe: pd.Dataframe, nettskjema_columns: dict) -> dict:
    dict_subm_title = {}
    df_selected = submission_dataframe[[nettskjema_columns['id_column'], nettskjema_columns['title_column']]]
    df_selected.set_index(nettskjema_columns['id_column'], inplace=True)
    return df_selected[nettskjema_columns['title_column']].to_dict()



def read_schedule(schedule_df: pd.DataFrame, schedule_columns: dict) -> tuple(dict, dict, dict, str):
    """
    Read schedule DataFrame and create dicts.
    NOTE workshops should have a unique number in the 'Number' column
    with a trailing 0 ('01', '02', ..., '10', '11', ...)
    """
    schedule_id_column = schedule_columns['id_column']
    schedule_title_column = schedule_columns['title_column']
    schedule_date_column = schedule_columns['date_column']
    # schedule_room_column = schedule_columns['room_column']
    # schedule_main_instructor_column = schedule_columns['main_instructor_column']
    # schedule_helper_instructor_column = schedule_columns['helper_instructor_column']
    # schedule_max_attendance = schedule_columns['max_attendance']
    schedule_time_column = schedule_columns['time_column']

    dict_id_name = schedule_df.set_index(schedule_id_column)[schedule_title_column].to_dict()
    dict_id_timeslot = schedule_df.set_index(schedule_id_column).T.to_dict()

    dict_title_wsids = schedule_df.set_index(schedule_title_column)[schedule_id_column].to_dict()

    networking_event_id = \
        schedule_df[schedule_df[schedule_title_column].str.startswith("Networking event")][schedule_id_column].values[
            0] if not schedule_df[schedule_df[schedule_title_column].str.startswith("Networking event")].empty else None

    dict_schedule_final = {}
    for date, group in schedule_df.groupby(schedule_date_column):
        dict_schedule_final[date] = {
            'morning': group[group[schedule_time_column] == 'morning'][
                [schedule_id_column, schedule_title_column]].to_dict('records'),
            'afternoon': group[group[schedule_time_column] == 'afternoon'][
                [schedule_id_column, schedule_title_column]].to_dict('records'),
            'whole_day': group[group[schedule_time_column] == 'full day'][
                [schedule_id_column, schedule_title_column]].to_dict('records')
        }

    return dict_schedule_final, dict_id_timeslot, dict_title_wsids, networking_event_id


def merge_submission_schedule(sumbmission_df: pd.DataFrame, schedule_df: pd.DataFrame, nettskjema_columns: dict,
                              schedule_columns: dict) -> pd.DataFrame:
    merged_df = pd.merge(sumbmission_df, schedule_df,
                         left_on=nettskjema_columns['title_column'],
                         right_on=schedule_columns['title_column'],
                         how='left'
                         )
    return merged_df


def annotate_networking_event(df: pd.DataFrame, schedule_columns: dict) -> pd.DataFrame:
    # If column 'title' start with 'Networking event' set networking event to True else False
    df[schedule_columns['networking_event_column']] = df[schedule_columns['title_column']].str.startswith(
        "Networking event")
    return df

def generate_ical_content(row, schedule_columns: dict, rooms: dict, yearly: dict) -> str:
    """
    Generate iCal content for a single workshop.

    Args:
        row (pd.Series): A row of the DataFrame containing workshop details.
        event_name (str): Name of the event.

    Returns:
        str: The iCal content.
    """
    datetime_start = datetime.strptime(row[schedule_columns['date_column']] + '-' + row[schedule_columns['start_time_column']], '%d.%m.%y-%H:%M')
    datetime_end = datetime.strptime(row[schedule_columns['date_column']] + '-' + row[schedule_columns['end_time_column']], '%d.%m.%y-%H:%M')


    ical_start = datetime_start.strftime("%Y%m%d") + "T" + datetime_start.strftime("%H%M%S")
    ical_end = datetime_start.strftime("%Y%m%d") + "T" + datetime_end.strftime("%H%M%S")
    workshop_title = row[schedule_columns['title_column']]
    room_name = row[schedule_columns['room_column']]
    room_url = rooms[room_name]['url'] if room_name in rooms else None
    event_name = yearly['event_name']

    ics_template = Template(filename='template/invite.ics')
    ics_content = ics_template.render(ical_start=ical_start,
                                      ical_end=ical_end,
                                      workshop_title=workshop_title,
                                      room_name=room_name,
                                      room_url=room_url,
                                      event_name=event_name)


    return ics_content

def write_ical_files(df, outdir_ics, schedule_columns, rooms, yearly):
    """
    Write individual ics files for each workshop from a pandas DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing workshop details.
        outdir_ics (str): Directory to save the ics files.
        event_name (str): Name of the event.
    """
    # Create ical folder if necessary
    Path(outdir_ics).mkdir(parents=True, exist_ok=True)
    # Remove any existing .ics files
    for ics_file in Path(outdir_ics).glob('*.ics'):
        if ics_file.is_file():
            ics_file.unlink()

    for _, row in df.iterrows():
        ics_content = generate_ical_content(row, schedule_columns, rooms, yearly)
        outpath_ics = os.path.join(outdir_ics, str(row[schedule_columns['id_column']]) + ".ics")
        with open(outpath_ics, 'w') as file:
            file.write(ics_content)


