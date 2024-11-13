from obiwow.data_reader_parser import parse_yaml, parse_csv_to_pandas, merge_submission_schedule, add_start_end_time_to_schedule, annotate_networking_event, \
    write_ical_files
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

    # Create Schedule table
    string_schedule_table = generate_schedule_table(df_schedule, schedule_columns, yearly)

    # Write html
    with open(paths['output']['html']['file_path'], 'w') as file:
        file.write('<h2>Agenda</h2>')
        file.write(string_schedule_table)
        # Write content of footer file
        with open(paths['input']['footer']['file_path'], 'r') as footer_file:
            file.write(footer_file.read())
        file.write("\n".join(list_workshop_body))

    write_ical_files(df_merge_submission_schedule,
                     paths['output']['ics']['dir_path'],
                     schedule_columns,
                     rooms,
                     yearly)

    print("Success! Output files written to disk.")
    print(f"Use '{paths['output']['html']['file_path']}' as raw html for the workshop website.")
    print(
        f"Copy '*.ics' files in the '{paths['output']['ics']['dir_path']}' folder so that they are in {yearly['ics_folder']}.")


if __name__ == "__main__":
    generate_html()
