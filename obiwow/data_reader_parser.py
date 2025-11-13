import json
import os
import re
from datetime import timedelta, datetime, time
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from mako.template import Template
import yaml
import pandas as pd


def add_duration_to_time(start_time_str: str, duration_str: str, workshop_title: str) -> str:
    """
    Add a duration to a start time and return the end time.

    Args:
        start_time_str (str): The start time in '%H:%M' format.
        duration_str (str): The duration string (e.g., '2 hours', '30 min').

    Returns:
        str: The end time in '%H:%M' format.
    """
    try:
        duration_str = duration_str.strip()
        start_time = datetime.strptime(start_time_str, '%H:%M')
        duration_match = re.match(r'(\d+)\s*(min|hours?)', duration_str)
        if not duration_match:
            raise ValueError(
                f'Invalid duration format: {duration_str}. Expected format: <number> min|hours for "{workshop_title}"')

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
    except Exception as e:
        print(f"WARNING: in add_duration_to_time: {e}")
        if start_time_str == '9:00':
            return '12:00'
        elif start_time_str == '13:00':
            return '16:00'
        return start_time_str
def expand_multiday_workshops(schedule_df: pd.DataFrame, schedule_columns: Dict[str, str]) -> pd.DataFrame:
    """
    Expand workshops with 'Length' in ['2 days', '3 days', '4 days', '5 days'] so each day becomes a separate entry.

    Each entry:
    - Has 'Workshop name' as 'Workshop name - Day N'
    - Uses the original Date as start, increments by 1 day per entry
    - Carries over relevant columns
    - Ensures valid 'Time' (full day) for each per-day entry if ambiguous
    - Final day's 'end_time' is 16:00 (used for ical)
    """
    multi_day_lengths = ['2 days', '3 days', '4 days', '5 days']
    expanded_rows = []
    for idx, row in schedule_df.iterrows():
        length = str(row[schedule_columns['duration_column']]).strip()
        if length in multi_day_lengths:
            num_days = int(length[0])  # parses '2' from '2 days' etc.
            start_date = row[schedule_columns['date_column']]
            try:
                start_dt = datetime.strptime(str(start_date), '%d.%m.%Y')
            except Exception:
                start_dt = pd.to_datetime(start_date, errors='coerce')
            for day in range(num_days):
                new_row = row.copy()
                day_dt = start_dt + timedelta(days=day)
                new_row[schedule_columns['date_column']] = day_dt.strftime('%d.%m.%Y')
                new_row[schedule_columns['title_column']] = (
                    f"{row[schedule_columns['title_column']]} - Day {day+1}"
                )
                # Default ambiguous time/duration to "full day" for expansion
                time_col = schedule_columns.get('time_column', 'Time')
                dur_col = schedule_columns.get('duration_column', 'Length')
                if not str(new_row.get(time_col, "")).strip() or str(new_row[time_col]).lower() in ['nan', '', 'none']:
                    new_row[time_col] = "full day"
                if not str(new_row.get(dur_col, "")).strip() or str(new_row[dur_col]).lower() in ['nan', '', 'none', length]:
                    new_row[dur_col] = "full day"
                # Add marker so .ics logic can find last day easily
                new_row['multi_day_final'] = ((day+1) == num_days)
                expanded_rows.append(new_row)
        else:
            # Non-multi-day workshops as-is
            row['multi_day_final'] = True
            expanded_rows.append(row)
    expanded_df = pd.DataFrame(expanded_rows)
    return expanded_df


def get_start_end_time(data: pd.Series, schedule_columns: Dict[str, str]) -> Tuple[str, str]:
    """
    Get the start and end time for a workshop based on the schedule data.

    Args:
        data (pd.Series): The schedule data row.
        schedule_columns (Dict[str, str]): The column names for the schedule data.

    Returns:
        Tuple[str, str]: The start and end time.
    """
    try:
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
                workshop_end_time = add_duration_to_time('9:00',
                                                         str(data[schedule_columns['duration_column']]),
                                                         data[schedule_columns['title_column']])
        elif data[schedule_columns['time_column']] == 'afternoon':
            if str(data[schedule_columns['duration_column']]) == 'nan':
                workshop_start_time = '13:00'
                workshop_end_time = '16:00'
            elif str(data[schedule_columns['duration_column']]) == 'half a day':
                workshop_start_time = '13:00'
                workshop_end_time = '16:00'
            else:
                workshop_start_time = '13:00'
                workshop_end_time = add_duration_to_time('13:00',
                                                         str(data[schedule_columns['duration_column']]),
                                                         data[schedule_columns['title_column']])
        return workshop_start_time, workshop_end_time
    except Exception as e:
        print(f"Error in get_start_end_time: {e}")
        return None, None


def add_start_end_time_to_schedule(schedule_df: pd.DataFrame, schedule_columns: Dict[str, str]) -> pd.DataFrame:
    """
    Add start and end times to the schedule DataFrame.

    Args:
        schedule_df (pd.DataFrame): The schedule DataFrame.
        schedule_columns (Dict[str, str]): The column names for the schedule data.

    Returns:
        pd.DataFrame: The updated schedule DataFrame with start and end times.
    """
    try:
        schedule_df[schedule_columns['start_time_column']] = None
        schedule_df[schedule_columns['end_time_column']] = None
        for index, row in schedule_df.iterrows():
            start_time, end_time = get_start_end_time(row, schedule_columns)
            schedule_df.at[index, schedule_columns['start_time_column']] = start_time
            schedule_df.at[index, schedule_columns['end_time_column']] = end_time
        return schedule_df
    except Exception as e:
        print(f"Error in add_start_end_time_to_schedule: {e}")
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
    except Exception as e:
        print(f"Error in parse_yaml: {e}")
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
    except Exception as e:
        print(f"Error in parse_csv_to_pandas: {e}")
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
    try:
        merged_df = pd.merge(submission_df, schedule_df,
                             left_on=nettskjema_columns['id_column'],
                             right_on=schedule_columns['nettskjema_id_column'],
                             how='right')
        return merged_df
    except Exception as e:
        print(f"Error in merge_submission_schedule: {e}")
        return pd.DataFrame()


def annotate_networking_event(df: pd.DataFrame, schedule_columns: Dict[str, str]) -> pd.DataFrame:
    """
    Annotate the DataFrame with networking event information.

    Args:
        df (pd.DataFrame): The DataFrame to annotate.
        schedule_columns (Dict[str, str]): The column names for the schedule data.

    Returns:
        pd.DataFrame: The annotated DataFrame.
    """
    try:
        df[schedule_columns['networking_event_column']] = df[schedule_columns['title_column']].str.startswith(
            "Networking event")
        return df
    except Exception as e:
        print(f"Error in annotate_networking_event: {e}")
        return df


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in {"", "nan", "none"}:
            return ""
        return stripped
    try:
        if pd.isna(value):  # type: ignore[arg-type]
            return ""
    except Exception:
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_schedule_date(date_value: Any) -> Optional[datetime]:
    normalized = _stringify(date_value)
    if not normalized:
        return None

    candidate_values: list[str] = [normalized]
    for separator in (' to ', ' - ', '-', '–', '—'):
        if separator in normalized:
            parts = normalized.split(separator)
            if len(parts) == 2:
                candidate = parts[0].strip()
                if candidate:
                    candidate_values.append(candidate)

    seen: set[str] = set()
    date_formats = (
        '%d.%m.%y',
        '%d.%m.%Y',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%Y-%m-%d',
    )

    for candidate in candidate_values:
        if candidate in seen:
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

    print(f"WARNING: Unable to parse schedule date '{date_value}'.")
    return None


def parse_schedule_time(time_value: Any) -> Optional[time]:
    normalized = _stringify(time_value)
    if not normalized:
        return None

    candidates = []
    if '-' in normalized:
        candidates.append(normalized.split('-', 1)[0].strip())
    candidates.append(normalized)

    for candidate in candidates:
        if not candidate:
            continue
        if re.match(r'^\d:\d{2}$', candidate):
            candidate = f"0{candidate}"
        for time_format in ('%H:%M', '%H.%M'):
            try:
                return datetime.strptime(candidate, time_format).time()
            except ValueError:
                continue

    print(f"WARNING: Unable to parse schedule time '{time_value}'.")
    return None


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
    try:
        # Use multi-day start/end if provided
        if (
            row.get('multi_day_start') is not None and
            row.get('multi_day_end') is not None
        ):
            (min_date, min_start) = row.get('multi_day_start')
            (max_date, max_end) = row.get('multi_day_end')
            datetime_start = datetime.combine(min_date.date(), min_start)
            datetime_end = datetime.combine(max_date.date(), max_end)
        else:
            parsed_date = parse_schedule_date(row.get(schedule_columns['date_column']))
            if not parsed_date:
                raise ValueError(f"Unable to parse date '{row.get(schedule_columns['date_column'])}'")
            start_time_value = parse_schedule_time(row.get(schedule_columns['start_time_column']))
            end_time_value = parse_schedule_time(row.get(schedule_columns['end_time_column']))
            if not start_time_value or not end_time_value:
                raise ValueError("Missing start or end time")

            datetime_start = datetime.combine(parsed_date.date(), start_time_value)
            datetime_end = datetime.combine(parsed_date.date(), end_time_value)
        if datetime_end <= datetime_start:
            datetime_end = datetime_start + timedelta(hours=1)

        ical_start = datetime_start.strftime("%Y%m%dT%H%M%S")
        ical_end = datetime_end.strftime("%Y%m%dT%H%M%S")
        workshop_title = _stringify(row.get(schedule_columns['title_column']))
        # Remove ' - Day N', ' — Day N', etc from workshop title
        import re
        workshop_title = re.sub(r"\s*[-—]\s*Day\s*\d+", "", workshop_title)
        room_name = _stringify(row.get(schedule_columns['room_column']))
        room_url = rooms.get(room_name, {}).get('url') if room_name else None
        event_name = yearly.get('event_name', '')

        project_root = Path(__file__).resolve().parent.parent
        template_path = os.path.join(project_root, 'template', 'invite.ics')

        ics_template = Template(filename=template_path)
        ics_content = ics_template.render(ical_start=ical_start,
                                          ical_end=ical_end,
                                          workshop_title=workshop_title,
                                          room_name=room_name,
                                          room_url=room_url,
                                          event_name=event_name)
        return ics_content
    except Exception as e:
        print(f"Error in generate_ical_content: {e} in '{row[schedule_columns['title_column']]}'")
        return ""


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
    try:
        Path(outdir_ics).mkdir(parents=True, exist_ok=True)
        for ics_file in Path(outdir_ics).glob('*.ics'):
            if ics_file.is_file():
                ics_file.unlink()

        # Preprocess multi-day workshops to set start/end times
        df = df.copy()
        title_col = schedule_columns['title_column']
        date_col = schedule_columns['date_column']
        start_col = schedule_columns['start_time_column']
        end_col = schedule_columns['end_time_column']
        df['multi_day_start'] = None
        df['multi_day_end'] = None

        grouped = df.groupby(df[title_col].astype(str).str.split(' - Day').str[0].str.strip())
        for base_title, group in grouped:
            # Only if multiple days
            if len(group) > 1:
                dates = group[date_col].apply(parse_schedule_date)
                starts = group[start_col].apply(parse_schedule_time)
                ends = group[end_col].apply(parse_schedule_time)

                # Find earliest start and latest end
                sorted_group = group.assign(date=dates)
                min_idx = dates.idxmin()
                max_idx = dates.idxmax()
                min_date = dates[min_idx]
                min_start = starts[min_idx]
                max_date = dates[max_idx]
                max_end = ends[max_idx]

                for idx in group.index:
                    df.at[idx, 'multi_day_start'] = (min_date, min_start)
                    df.at[idx, 'multi_day_end'] = (max_date, max_end)

        for _, row in df.iterrows():
            ics_content = generate_ical_content(row, schedule_columns, rooms, yearly)
            outpath_ics = os.path.join(outdir_ics, str(row[schedule_columns['id_column']]) + ".ics")
            with open(outpath_ics, 'w') as file:
                file.write(ics_content)
    except Exception as e:
        print(f"Error in write_ical_files: {e}")


def write_schedule_json(schedule_df: pd.DataFrame, schedule_columns: dict, output_file: str) -> None:
    """
    Create a JSON file from the schedule DataFrame.

    Args:
        schedule_df (pd.DataFrame): The schedule DataFrame.
        schedule_columns (dict): Dictionary mapping column names for the schedule data.
        output_file (str): The path to the output JSON file.
    """
    try:
        schedule_dict = {}

        for _, row in schedule_df.iterrows():
            workshop_id = row[schedule_columns['id_column']]
            parsed_date = parse_schedule_date(row.get(schedule_columns['date_column']))
            formatted_date = parsed_date.strftime('%d.%m.%y') if parsed_date else _stringify(
                row.get(schedule_columns['date_column'])
            )

            room_name = _stringify(row.get(schedule_columns['room_column']))
            main_instructor = _stringify(row.get(schedule_columns['main_instructor_column']))
            helper_instructor = _stringify(row.get(schedule_columns['helper_instructor_column']))
            title = _stringify(row.get(schedule_columns['title_column']))

            max_attendance_raw = row.get(schedule_columns['max_attendance'])
            if max_attendance_raw is None or (isinstance(max_attendance_raw, float) and pd.isna(max_attendance_raw)):
                max_attendance_value = None
            else:
                try:
                    max_attendance_value = int(max_attendance_raw)
                except (TypeError, ValueError):
                    max_attendance_value = _stringify(max_attendance_raw)

            start_time_value = _stringify(row.get(schedule_columns['start_time_column']))
            end_time_value = _stringify(row.get(schedule_columns['end_time_column']))
            if start_time_value and end_time_value:
                timeslot = f"{start_time_value}-{end_time_value}"
            else:
                timeslot = start_time_value or end_time_value or ""

            schedule_dict[workshop_id] = {
                "date": formatted_date,
                "room": room_name,
                "main_instructor": main_instructor,
                "helper": helper_instructor,
                "title": title,
                "max_attendance": max_attendance_value,
                "timeslot": timeslot
            }

        with open(output_file, 'w') as json_file:
            json.dump(schedule_dict, json_file, indent=4)
    except Exception as e:
        print(f"Error in write_schedule_json: {e}")


def standardise_time_of_day(time: str) -> str:
    """
    Standardise the time of day string.

    Args:
        time (str): The time of day string.

    Returns:
        str: The standardised time of day string.
    """
    time_of_day_mapping = {
        'morning': ['morning', 'morgen'],
        'afternoon': ['afternoon', 'ettermiddag'],
        'all day': ['all day', 'whole day', 'full day'],
        'half a day': ['half a day', 'halv dag']
    }

    for time_of_day, time_of_day_synonyms in time_of_day_mapping.items():
        if time in time_of_day_synonyms:
            return time_of_day
    return time


def standardise_time_of_day_column(df: pd.DataFrame, dict_columns: dict) -> pd.DataFrame:
    """
    Standardise the time of day column in the DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to standardise.
        dict_columns (dict): The dictionary containing column names.

    Returns:
        pd.DataFrame: The updated DataFrame
    """
    if 'time_column' in dict_columns:
        df[dict_columns['time_column']] = df[dict_columns['time_column']].apply(standardise_time_of_day)
    if 'duration_column' in dict_columns:
        df[dict_columns['duration_column']] = df[dict_columns['duration_column']].apply(standardise_time_of_day)
    return df


def write_html_page(full_page_html_rendered: str, paths: dict) -> None:
    """
    Write the full HTML page to disk.

    Args:
        full_page_html_rendered (str): The full HTML page as a string.
        paths (dict): The dictionary containing all configuration data.
    """

    try:
        with open(paths['output']['html']['file_path'], 'w') as file:
            file.write(full_page_html_rendered)
    except Exception as e:
        print(f"Error in write_html_page: {e}")
        raise e
