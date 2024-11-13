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
    datetime_start = datetime.strptime(
        row[schedule_columns['date_column']] + '-' + row[schedule_columns['start_time_column']], '%d.%m.%y-%H:%M')
    datetime_end = datetime.strptime(
        row[schedule_columns['date_column']] + '-' + row[schedule_columns['end_time_column']], '%d.%m.%y-%H:%M')

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


def write_ical_files(df: pd.DataFrame, outdir_ics: str, schedule_columns: dict, rooms: dict, yearly: dict) -> None:
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
