from obiwow.data_reader_parser import standardise_time_of_day_column, write_html_page
from obiwow.data_reader_parser import (
    parse_yaml, parse_csv_to_pandas, merge_submission_schedule,
    add_start_end_time_to_schedule, annotate_networking_event, write_ical_files, write_schedule_json,
    expand_multiday_workshops
)
from obiwow.tsv_to_html import generate_workshop_body, generate_schedule_table, generate_full_html_page


def import_all_config() -> dict:
    """
    Import all configuration files.

    Returns:
        dict: A dictionary containing all configuration data.
    """
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


def generate_html() -> None:
    """
    Generate the HTML and iCalendar files for the workshop website.
    """
    DEBUG = False # for printing out debugging info
    config = import_all_config()

    # registration_open = config['yearly'].get('registration_open', False)
    paths = config['paths']
    yearly = config['yearly']
    nettskjema_columns = config['nettskjema_columns']
    schedule_columns = config['schedule_columns']
    rooms = config['rooms']

    df_submissions = parse_csv_to_pandas(paths['input']['survey_results']['file_path'],
                                         paths['input']['survey_results']['delimiter'])
    df_schedule = parse_csv_to_pandas(paths['input']['schedule']['file_path'],
                                      paths['input']['schedule']['delimiter'])

    title_column = schedule_columns['title_column']
    if df_schedule is not None and title_column in df_schedule.columns:
        df_schedule = df_schedule[
            df_schedule[title_column].fillna("").astype(str).str.strip().ne("Example")
        ]

        # Expand multi-day workshops to per-day entries (with titled suffixes, per requirements)
        df_schedule = expand_multiday_workshops(df_schedule, schedule_columns)
    # Remove rows with cancelled workshops
    #df_schedule = df_schedule[df_schedule[schedule_columns['status_column']] != 'cancelled']

    # Assign start/end time columns to the schedule DataFrame
    df_schedule = add_start_end_time_to_schedule(df_schedule, schedule_columns)
    if DEBUG:
        # DEBUG: print the DataFrame columns and first rows to verify time columns
        print("Schedule DataFrame columns after time assignment:", df_schedule.columns.tolist())
        print(df_schedule[[schedule_columns['title_column'],
                        schedule_columns['date_column'],
                        schedule_columns.get('time_column', 'Time'),
                        schedule_columns.get('duration_column', 'Length'),
                        schedule_columns.get('start_time_column', 'Start time'),
                        schedule_columns.get('end_time_column', 'End time')]].head(10))
        # DEBUG: print first few expanded schedule entries and their computed times
        print(df_schedule[[schedule_columns['title_column'],
                        schedule_columns['date_column'],
                        schedule_columns.get('time_column', 'Time'),
                        schedule_columns.get('duration_column', 'Length'),
                        schedule_columns.get('start_time_column', 'start_time'),
                        schedule_columns.get('end_time_column', 'end_time')]].head(10))
    standardise_time_of_day_column(df_schedule, schedule_columns)
    df_schedule = add_start_end_time_to_schedule(df_schedule, schedule_columns)
    df_schedule = annotate_networking_event(df_schedule, schedule_columns)

    df_merge_submission_schedule = merge_submission_schedule(df_submissions, df_schedule, nettskjema_columns,
                                                             schedule_columns)

    list_workshop_body = generate_workshop_body(df_merge_submission_schedule, nettskjema_columns, schedule_columns,
                                                yearly, rooms)

    string_schedule_table = generate_schedule_table(df_schedule, schedule_columns, yearly)


    string_full_page = generate_full_html_page(string_schedule_table, list_workshop_body, yearly, paths)

    write_html_page(string_full_page, paths)

    write_ical_files(df_merge_submission_schedule, paths['output']['ics']['dir_path'], schedule_columns, rooms, yearly)

    write_schedule_json(df_schedule, schedule_columns, paths['output']['schedule_json']['file_path'])

    print("Success! Output files written to disk.")
    print(f"Use '{paths['output']['html']['file_path']}' as raw html for the workshop website.")
    print(
        f"Copy '*.ics' files in the '{paths['output']['ics']['dir_path']}' folder so that they are in {paths['output']['ics']['dir_path']}.")


import subprocess

if __name__ == "__main__":
    generate_html()
    # Generate the markdown room schedule as the final step
    subprocess.run(["python3", "generate_room_schedule.py"], check=True)
