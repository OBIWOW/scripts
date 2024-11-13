import os
import re
from datetime import timedelta, datetime
from pathlib import Path
from typing import Tuple, Dict, Any
from mako.template import Template
import yaml
import pandas as pd


def add_duration_to_time(start_time_str: str, duration_str: str) -> str:
    """
    Add a duration to a start time and return the end time.

    Args:
        start_time_str (str): The start time in '%H:%M' format.
        duration_str (str): The duration string (e.g., '2 hours', '30 min').

    Returns:
        str: The end time in '%H:%M' format.
    """
    duration_str = duration_str.strip()
    start_time = datetime.strptime(start_time_str, '%H:%M')
    duration_match = re.match(r'(\d+)\s*(min|hours?)', duration_str)
    if not duration_match:
        print(f'Invalid duration format: {duration_str}, expected format: <number> <unit> (e.g., 2 hours, 30 min)')
        if start_time_str == '9:00':
            return '12:00'
        elif start_time_str == '13:00':
            return '16:00'
        return start_time_str

    duration_value = int(duration_match.group(1))
    duration_unit = duration_match.group(2)

    if 'hour' in duration_unit:
        duration = timedelta(hours=duration_value)
    elif 'min' in duration_unit:
        duration = timedelta(minutes=duration_value)
    else:
        raise ValueError("Invalid duration unit")

    end_time = start_time + duration
    return end_time.strftime('%H:%M')


def get_start_end_time(data: pd.Series, schedule_columns: Dict[str, str]) -> Tuple[str, str]:
    """
    Get the start and end time for a workshop based on the schedule data.

    Args:
        data (pd.Series): The schedule data row.
        schedule_columns (Dict[str, str]): The column names for the schedule data.

    Returns:
        Tuple[str, str]: The start and end time.
    """
    workshop_start_time = None
    workshop_end_time = None
    if data[schedule_columns['duration_column']] == 'all day':
        workshop_start_time = '9:00'
        workshop_end_time = '16:00'
    elif data[schedule_columns['time_column']] == 'morning':
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


def add_start_end_time_to_schedule(schedule_df: pd.DataFrame, schedule_columns: Dict[str, str]) -> pd.DataFrame:
    """
    Add start and end times to the schedule DataFrame.

    Args:
        schedule_df (pd.DataFrame): The schedule DataFrame.
        schedule_columns (Dict[str, str]): The column names for the schedule data.

    Returns:
        pd.DataFrame: The updated schedule DataFrame with start and end times.
    """
    schedule_df[schedule_columns['start_time_column']] = None
    schedule_df[schedule_columns['end_time_column']] = None
    for index, row in schedule_df.iterrows():
        start_time, end_time = get_start_end_time(row, schedule_columns)
        schedule_df.at[index, schedule_columns['start_time_column']] = start_time
        schedule_df.at[index, schedule_columns['end_time_column']] = end_time

    return schedule_df


def parse_yaml(path_conf: str) -> Dict[str, Any]:
    """
    Parse a YAML configuration file.

    Args:
        path_conf (str): The path to the YAML configuration file.

    Returns:
        Dict[str, Any]: The parsed configuration as a dictionary.
    """
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


def parse_csv_to_pandas(csv_content: str, delimiter: str) -> pd.DataFrame:
    """
    Parse a CSV file into a pandas DataFrame.

    Args:
        csv_content (str): The path to the CSV file.
        delimiter (str): The delimiter used in the CSV file.

    Returns:
        pd.DataFrame: The parsed DataFrame.
    """
    try:
        df = pd.read_csv(csv_content, delimiter=delimiter, header=0)
    except FileNotFoundError:
        print(f"File {csv_content} not found.")
        df = None
    return df


def merge_submission_schedule(submission_df: pd.DataFrame, schedule_df: pd.DataFrame,
                              nettskjema_columns: Dict[str, str],
                              schedule_columns: Dict[str, str]) -> pd.DataFrame:
    """
    Merge the submission and schedule DataFrames.

    Args:
        submission_df (pd.DataFrame): The submission DataFrame.
        schedule_df (pd.DataFrame): The schedule DataFrame.
        nettskjema_columns (Dict[str, str]): The column names for the nettskjema data.
        schedule_columns (Dict[str, str]): The column names for the schedule data.

    Returns:
        pd.DataFrame: The merged DataFrame.
    """
    merged_df = pd.merge(submission_df, schedule_df,
                         left_on=nettskjema_columns['title_column'],
                         right_on=schedule_columns['title_column'],
                         how='left')
    return merged_df


def annotate_networking_event(df: pd.DataFrame, schedule_columns: Dict[str, str]) -> pd.DataFrame:
    """
    Annotate the DataFrame with networking event information.

    Args:
        df (pd.DataFrame): The DataFrame to annotate.
        schedule_columns (Dict[str, str]): The column names for the schedule data.

    Returns:
        pd.DataFrame: The annotated DataFrame.
    """
    df[schedule_columns['networking_event_column']] = df[schedule_columns['title_column']].str.startswith(
        "Networking event")
    return df


def generate_ical_content(row: pd.Series, schedule_columns: Dict[str, str], rooms: Dict[str, Dict[str, str]],
                          yearly: Dict[str, str]) -> str:
    """
    Generate the iCalendar content for a workshop.

    Args:
        row (pd.Series): The row of the schedule data.
        schedule_columns (Dict[str, str]): The column names for the schedule data.
        rooms (Dict[str, Dict[str, str]]): The room information.
        yearly (Dict[str, str]): The yearly configuration values.

    Returns:
        str: The iCalendar content.
    """
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


def write_ical_files(df: pd.DataFrame, outdir_ics: str, schedule_columns: Dict[str, str],
                     rooms: Dict[str, Dict[str, str]], yearly: Dict[str, str]) -> None:
    """
    Write iCalendar files for each workshop.

    Args:
        df (pd.DataFrame): The DataFrame containing the schedule data.
        outdir_ics (str): The output directory for the iCalendar files.
        schedule_columns (Dict[str, str]): The column names for the schedule data.
        rooms (Dict[str, Dict[str, str]]): The room information.
        yearly (Dict[str, str]): The yearly configuration values.
    """
    Path(outdir_ics).mkdir(parents=True, exist_ok=True)
    for ics_file in Path(outdir_ics).glob('*.ics'):
        if ics_file.is_file():
            ics_file.unlink()

    for _, row in df.iterrows():
        ics_content = generate_ical_content(row, schedule_columns, rooms, yearly)
        outpath_ics = os.path.join(outdir_ics, str(row[schedule_columns['id_column']]) + ".ics")
        with open(outpath_ics, 'w') as file:
            file.write(ics_content)
