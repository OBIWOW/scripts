import sys

import pandas as pd

from data_reader_parser import merge_submission_schedule, add_start_end_time_to_schedule
from obiwow.data_reader_parser import parse_yaml, parse_csv_to_pandas, get_submission_ID_dict, read_schedule
from obiwow.tsv_to_html import read_workshops, create_schedule_table
#     get_submission_ID_dict, read_schedule, read_workshops, create_schedule_table,
#     adjust_event, write_html, write_ical
# )


import json
from pathlib import Path
import os

from pprint import pprint

from obiwow.tsv_to_html import generate_workshop_body


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
    df_submissions = parse_csv_to_pandas(paths['input']['survey_results']['file_path'], paths['input']['survey_results']['delimiter'])
    df_schedule = parse_csv_to_pandas(paths['input']['schedule']['file_path'], paths['input']['schedule']['delimiter'])
    df_schedule = add_start_end_time_to_schedule(df_schedule, schedule_columns)

    df_merge_submission_schedule = merge_submission_schedule(df_submissions, df_schedule, nettskjema_columns, schedule_columns)

    test = generate_workshop_body(df_merge_submission_schedule,
                                    nettskjema_columns,
                                    schedule_columns,
                                    yearly,
                                    rooms)

    with(open('test.html', 'w')) as f:
        for line in test:
            f.write(line + '\n')

    # print full dataframes
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        print(df_merge_submission_schedule)

    # create schedule table html
    # table_header_schedule, list_line_schedule = create_schedule_table(dict_schedule_final)
    #
    # # adjust for Networking event: should link to its own webpage
    # list_line_schedule = adjust_event(list_line_schedule, networking_event_id, yearly['networking_event_url'])
    #
    # # collect all output in html format
    # write_html(table_header_schedule, list_line_schedule, list_html_section, paths['footer'])
    #
    # # write ical files
    # write_ical(paths['outdir_ics'], dict_id_timeslot, yearly['event_name'])
    #
    # print("Success! Output files written to disk.")
    # print(f"Use '{paths['outfile']}' as raw html for the workshop website.")
    # print(f"Copy '*.ics' files in the '{paths['outdir_ics']}' folder so that they are in {yearly['ics_folder']}.")

if __name__ == "__main__":
    generate_html()