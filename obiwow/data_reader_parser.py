from __future__ import annotations

import yaml
import pandas as pd


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


import pandas as pd


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
    print(sumbmission_df)
    print(schedule_df)
    merged_df = pd.merge(sumbmission_df, schedule_df,
                      left_on=nettskjema_columns['title_column'],
                      right_on=schedule_columns['title_column'],
                        how='left'
                      )
    return merged_df
