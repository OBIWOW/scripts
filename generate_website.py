import sys

import pandas as pd
import json
from pathlib import Path
import os

from pprint import pprint

from data_reader_parser import merge_submission_schedule, add_start_end_time_to_schedule, annotate_networking_event, \
    write_ical_files
from obiwow.data_reader_parser import parse_yaml, parse_csv_to_pandas
from obiwow.tsv_to_html import generate_workshop_body, generate_schedule_table


def import_all_config():
    paths_config = parse_yaml('config/paths.yaml')
    yearly_config = parse_yaml('config/yearly_config.yaml')
    nettskjema_columns = parse_yaml('config/nettskjema_columns.yaml')
    schedule_columns = parse_yaml('config/schedule_columns.yaml')
    rooms_config = parse_yaml('config/rooms.yaml')

    return {
        'paths': paths_config,
        'yearly': yearly_config,
        'nettskjema_columns': nettskjema_columns,
        'schedule_columns': schedule_columns,
        'rooms': rooms_config
    }


def generate_html():
    config = import_all_config()

    print(config)

    registration_open = config['yearly'].get('registration_open', False)
    paths = config['paths']
    yearly = config['yearly']
    nettskjema_columns = config['nettskjema_columns']
    schedule_columns = config['schedule_columns']
    rooms = config['rooms']

    # Parse input files
    # Read and parse workshop descriptions
    df_submissions = parse_csv_to_pandas(paths['input']['survey_results']['file_path'],
                                         paths['input']['survey_results']['delimiter'])
    df_schedule = parse_csv_to_pandas(paths['input']['schedule']['file_path'], paths['input']['schedule']['delimiter'])
    df_schedule = add_start_end_time_to_schedule(df_schedule, schedule_columns)
    df_schedule = annotate_networking_event(df_schedule, schedule_columns)

    df_merge_submission_schedule = merge_submission_schedule(df_submissions, df_schedule, nettskjema_columns,
                                                             schedule_columns)

    list_workshop_body = generate_workshop_body(df_merge_submission_schedule,
                                  nettskjema_columns,
                                  schedule_columns,
                                  yearly,
                                  rooms)


    # print full dataframes
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        print(df_merge_submission_schedule)
    # write pandas dataframes to csv
    df_merge_submission_schedule.to_csv('df_merge_submission_schedule.csv')
    # with pd.option_context('display.max_rows', None, 'display.max_columns', None):
    #     print(df_schedule)

    # Create Schedule table
    string_schedule_table = generate_schedule_table(df_schedule, schedule_columns, yearly)

    # Write html
    with open(paths['output']['html']['file_path'], 'w') as file:
        file.write(string_schedule_table)
        file.write("\n".join(list_workshop_body))

    write_ical_files(df_merge_submission_schedule,
                     paths['output']['ics']['dir_path'],
                     schedule_columns,
                     rooms,
                     yearly)

    #
    # # write ical files
    # write_ical(paths['outdir_ics'], dict_id_timeslot, yearly['event_name'])
    #
    # print("Success! Output files written to disk.")
    # print(f"Use '{paths['outfile']}' as raw html for the workshop website.")
    # print(f"Copy '*.ics' files in the '{paths['outdir_ics']}' folder so that they are in {yearly['ics_folder']}.")


if __name__ == "__main__":
    generate_html()
