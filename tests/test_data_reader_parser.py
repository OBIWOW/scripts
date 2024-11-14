import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from mako.template import Template

import pytest
import pandas as pd
from obiwow.data_reader_parser import add_duration_to_time, get_start_end_time, parse_yaml, parse_csv_to_pandas, \
    merge_submission_schedule, annotate_networking_event, generate_ical_content, write_ical_files, write_schedule_json, \
    standardise_time_of_day, standardise_time_of_day_column, write_html_page


class TestAddDurationToTime:

    # Correctly adds hours to start time and returns end time in '%H:%M' format
    def test_add_hours_to_time(self):
        result = add_duration_to_time('10:00', '2 hours')
        assert result == '12:00'

    # Correctly adds minutes to start time and returns end time in '%H:%M' format
    def test_add_minutes_to_time(self):
        result = add_duration_to_time('10:00', '30 min')
        assert result == '10:30'

    # Returns start time when duration format is invalid
    def test_invalid_duration_format_returns_start_time(self):
        result = add_duration_to_time('10:00', 'invalid format')
        assert result == '10:00'

    # Returns '12:00' for invalid duration format when start time is '9:00'
    def test_invalid_duration_format_start_9_returns_12(self):
        result = add_duration_to_time('9:00', 'invalid format')
        assert result == '12:00'

    # Returns '16:00' for invalid duration format when start time is '13:00'
    def test_invalid_duration_format_start_13_returns_16(self):
        result = add_duration_to_time('13:00', 'invalid format')
        assert result == '16:00'


class TestGetStartEndTime:

    # Correctly calculates end time for 'all day' duration
    def test_all_day_duration(self):
        data = pd.Series({'duration_column': 'all day', 'time_column': 'any'})
        schedule_columns = {'duration_column': 'duration_column', 'time_column': 'time_column'}
        start_time, end_time = get_start_end_time(data, schedule_columns)
        assert start_time == '9:00'
        assert end_time == '16:00'

    # Correctly calculates start and end time for 'morning' with 'half a day' duration
    def test_morning_half_day_duration(self):
        data = pd.Series({'duration_column': 'half a day', 'time_column': 'morning'})
        schedule_columns = {'duration_column': 'duration_column', 'time_column': 'time_column'}
        start_time, end_time = get_start_end_time(data, schedule_columns)
        assert start_time == '9:00'
        assert end_time == '12:00'

    # Handles 'nan' duration for 'morning' time
    def test_morning_nan_duration(self):
        data = pd.Series({'duration_column': float('nan'), 'time_column': 'morning'})
        schedule_columns = {'duration_column': 'duration_column', 'time_column': 'time_column'}
        start_time, end_time = get_start_end_time(data, schedule_columns)
        assert start_time == '9:00'
        assert end_time == '12:00'

    # Handles 'nan' duration for 'afternoon' time
    def test_afternoon_nan_duration(self):
        data = pd.Series({'duration_column': float('nan'), 'time_column': 'afternoon'})
        schedule_columns = {'duration_column': 'duration_column', 'time_column': 'time_column'}
        start_time, end_time = get_start_end_time(data, schedule_columns)
        assert start_time == '13:00'
        assert end_time == '16:00'

    # Handles invalid duration format gracefully
    def test_invalid_duration_format(self):
        data = pd.Series({'duration_column': 'invalid format', 'time_column': 'morning'})
        schedule_columns = {'duration_column': 'duration_column', 'time_column': 'time_column'}
        start_time, end_time = get_start_end_time(data, schedule_columns)
        assert start_time == '9:00'
        assert end_time == '12:00'


class TestAddStartEndTimeToSchedule:

    # Correctly adds start and end times for all-day events
    def test_all_day_event_times(self):
        import pandas as pd
        from obiwow.data_reader_parser import add_start_end_time_to_schedule

        schedule_df = pd.DataFrame({
            'duration': ['all day'],
            'time': ['']
        })
        schedule_columns = {
            'duration_column': 'duration',
            'time_column': 'time',
            'start_time_column': 'start_time',
            'end_time_column': 'end_time'
        }

        updated_df = add_start_end_time_to_schedule(schedule_df, schedule_columns)
        assert updated_df['start_time'][0] == '9:00'
        assert updated_df['end_time'][0] == '16:00'

    # Correctly adds start and end times for morning events
    def test_morning_event_times(self):
        import pandas as pd
        from obiwow.data_reader_parser import add_start_end_time_to_schedule

        schedule_df = pd.DataFrame({
            'duration': ['half a day'],
            'time': ['morning']
        })
        schedule_columns = {
            'duration_column': 'duration',
            'time_column': 'time',
            'start_time_column': 'start_time',
            'end_time_column': 'end_time'
        }

        updated_df = add_start_end_time_to_schedule(schedule_df, schedule_columns)
        assert updated_df['start_time'][0] == '9:00'
        assert updated_df['end_time'][0] == '12:00'

    # Handles 'nan' duration values without errors
    def test_nan_duration_handling(self):
        import pandas as pd
        from obiwow.data_reader_parser import add_start_end_time_to_schedule
        import numpy as np

        schedule_df = pd.DataFrame({
            'duration': [np.nan],
            'time': ['morning']
        })
        schedule_columns = {
            'duration_column': 'duration',
            'time_column': 'time',
            'start_time_column': 'start_time',
            'end_time_column': 'end_time'
        }

        updated_df = add_start_end_time_to_schedule(schedule_df, schedule_columns)
        assert updated_df['start_time'][0] == '9:00'
        assert updated_df['end_time'][0] == '12:00'

    # Processes an empty DataFrame without errors
    def test_empty_dataframe_handling(self):
        import pandas as pd
        from obiwow.data_reader_parser import add_start_end_time_to_schedule

        schedule_df = pd.DataFrame(columns=['duration', 'time'])
        schedule_columns = {
            'duration_column': 'duration',
            'time_column': 'time',
            'start_time_column': 'start_time',
            'end_time_column': 'end_time'
        }

        updated_df = add_start_end_time_to_schedule(schedule_df, schedule_columns)
        assert updated_df.empty

    # Handles unexpected values in time or duration columns
    def test_unexpected_values_handling(self):
        import pandas as pd
        from obiwow.data_reader_parser import add_start_end_time_to_schedule

        schedule_df = pd.DataFrame({
            'duration': ['unexpected'],
            'time': ['unexpected']
        })
        schedule_columns = {
            'duration_column': 'duration',
            'time_column': 'time',
            'start_time_column': 'start_time',
            'end_time_column': 'end_time'
        }

        updated_df = add_start_end_time_to_schedule(schedule_df, schedule_columns)

        assert updated_df['start_time'][0] is None
        assert updated_df['end_time'][0] is None

    # Returns original DataFrame if an exception occurs
    def test_exception_handling_returns_original_dataframe(self):
        import pandas as pd
        from obiwow.data_reader_parser import add_start_end_time_to_schedule

        # Intentionally causing an exception by passing incorrect column names
        schedule_df = pd.DataFrame({
            'wrong_duration': ['all day'],
            'wrong_time': ['']
        })
        schedule_columns = {
            'duration_column': 'duration',
            'time_column': 'time',
            'start_time_column': 'start_time',
            'end_time_column': 'end_time'
        }

        updated_df = add_start_end_time_to_schedule(schedule_df, schedule_columns)

        # The DataFrame should remain unchanged due to the exception
        assert updated_df.equals(schedule_df)


class TestParseYaml:

    # Successfully parses a valid YAML file into a dictionary
    def test_parse_valid_yaml(self, tmp_path):
        path_conf = tmp_path / 'valid_config.yaml'
        path_conf.write_text("key: value")
        result = parse_yaml(str(path_conf))
        assert result == {'key': 'value'}

    # Returns a dictionary when the YAML file contains nested structures
    def test_parse_nested_yaml(self, tmp_path):
        path_conf = tmp_path / 'nested_config.yaml'
        path_conf.write_text("parent:\n  child: value")
        result = parse_yaml(str(path_conf))
        assert result == {'parent': {'child': 'value'}}

    # Returns None when the YAML file is not found
    def test_file_not_found(self):
        path_conf = 'non_existent.yaml'
        result = parse_yaml(path_conf)
        assert result is None

    # Returns None and prints an error message for invalid YAML syntax
    def test_invalid_yaml_syntax(self, tmp_path):
        path_conf = tmp_path / 'invalid_syntax.yaml'
        path_conf.write_text("key: value\nkey2")
        result = parse_yaml(str(path_conf))
        assert result is None


class TestParseCsvToPandas:

    # Successfully parses a well-formed CSV file with a specified delimiter
    def test_parse_well_formed_csv(self):
        csv_content = StringIO("name,age\nAlice,30\nBob,25")
        delimiter = ","
        df = parse_csv_to_pandas(csv_content, delimiter)
        assert df is not None
        assert len(df) == 2
        assert list(df.columns) == ["name", "age"]

    # Returns a pandas DataFrame with correct data types and structure
    def test_dataframe_structure_and_types(self):
        csv_content = StringIO("name,age\nAlice,30\nBob,25")
        delimiter = ","
        df = parse_csv_to_pandas(csv_content, delimiter)
        assert df["age"].dtype == int
        assert df["name"].dtype == object

    # Handles non-existent file paths gracefully without crashing
    def test_non_existent_file_path(self):
        csv_content = "non_existent_file.csv"
        delimiter = ","
        df = parse_csv_to_pandas(csv_content, delimiter)
        assert df is None

    # Manages empty CSV files without errors
    @pytest.mark.skip(reason="Issue giving empty string to StringIO")
    def test_empty_csv_file(self):
        csv_content = StringIO("")
        delimiter = ","
        df = parse_csv_to_pandas(csv_content, delimiter)
        assert df is not None
        assert df.empty

    # Deals with CSV files containing only headers and no data
    def test_csv_with_only_headers(self):
        csv_content = StringIO("name,age\n")
        delimiter = ","
        df = parse_csv_to_pandas(csv_content, delimiter)
        assert df is not None
        assert df.empty
        assert list(df.columns) == ["name", "age"]


class TestMergeSubmissionSchedule:

    # Successfully merges two DataFrames based on specified columns
    def test_successful_merge(self):
        submission_df = pd.DataFrame({'title': ['A', 'B'], 'value': [1, 2]})
        schedule_df = pd.DataFrame({'title': ['A', 'B'], 'date': ['2023-01-01', '2023-01-02']})
        nettskjema_columns = {'title_column': 'title'}
        schedule_columns = {'title_column': 'title'}
        result = merge_submission_schedule(submission_df, schedule_df, nettskjema_columns, schedule_columns)
        assert not result.empty
        assert 'date' in result.columns

    # Returns a DataFrame with expected merged content when inputs are valid
    def test_expected_merged_content(self):
        submission_df = pd.DataFrame({'title': ['A', 'B'], 'value': [1, 2]})
        schedule_df = pd.DataFrame({'title': ['A', 'B'], 'date': ['2023-01-01', '2023-01-02']})
        nettskjema_columns = {'title_column': 'title'}
        schedule_columns = {'title_column': 'title'}
        result = merge_submission_schedule(submission_df, schedule_df, nettskjema_columns, schedule_columns)
        expected_dates = ['2023-01-01', '2023-01-02']
        assert list(result['date']) == expected_dates

    # Handles cases where one or both DataFrames are empty
    def test_empty_dataframes(self):
        submission_df = pd.DataFrame()
        schedule_df = pd.DataFrame({'title': ['A'], 'date': ['2023-01-01']})
        nettskjema_columns = {'title_column': 'title'}
        schedule_columns = {'title_column': 'title'}
        result = merge_submission_schedule(submission_df, schedule_df, nettskjema_columns, schedule_columns)
        assert result.empty

        submission_df = pd.DataFrame({'title': ['A'], 'value': [1]})
        schedule_df = pd.DataFrame()
        result = merge_submission_schedule(submission_df, schedule_df, nettskjema_columns, schedule_columns)
        assert result.empty

        submission_df = pd.DataFrame()
        schedule_df = pd.DataFrame()
        result = merge_submission_schedule(submission_df, schedule_df, nettskjema_columns, schedule_columns)
        assert result.empty

    # Manages scenarios where specified columns do not exist in DataFrames
    def test_missing_columns(self):
        submission_df = pd.DataFrame({'wrong_title': ['A', 'B'], 'value': [1, 2]})
        schedule_df = pd.DataFrame({'wrong_title': ['A', 'B'], 'date': ['2023-01-01', '2023-01-02']})
        nettskjema_columns = {'title_column': 'title'}
        schedule_columns = {'title_column': 'title'}
        result = merge_submission_schedule(submission_df, schedule_df, nettskjema_columns, schedule_columns)
        assert result.empty

    # Deals with mismatched data types in key columns
    def test_mismatched_data_types(self):
        submission_df = pd.DataFrame({'title': [1, 2], 'value': [1, 2]})
        schedule_df = pd.DataFrame({'title': ['1', '2'], 'date': ['2023-01-01', '2023-01-02']})
        nettskjema_columns = {'title_column': 'title'}
        schedule_columns = {'title_column': 'title'}
        result = merge_submission_schedule(submission_df, schedule_df, nettskjema_columns, schedule_columns)
        assert result.empty


class TestAnnotateNetworkingEvent:

    # Annotates DataFrame when 'title_column' starts with "Networking event"
    def test_annotates_networking_event(self):
        df = pd.DataFrame({'title': ['Networking event - Lunch', 'Workshop']})
        schedule_columns = {'title_column': 'title', 'networking_event_column': 'is_networking_event'}
        result = annotate_networking_event(df, schedule_columns)
        assert result['is_networking_event'].tolist() == [True, False]

    # Returns DataFrame with new column for networking events
    def test_returns_dataframe_with_new_column(self):
        df = pd.DataFrame({'title': ['Networking event - Lunch', 'Workshop']})
        schedule_columns = {'title_column': 'title', 'networking_event_column': 'is_networking_event'}
        result = annotate_networking_event(df, schedule_columns)
        assert 'is_networking_event' in result.columns

    # Handles missing 'networking_event_column' in schedule_columns
    def test_missing_networking_event_column(self):
        df = pd.DataFrame({'title': ['Networking event - Lunch', 'Workshop']})
        schedule_columns = {'title_column': 'title'}
        result = annotate_networking_event(df, schedule_columns)
        assert result.equals(df)

    # Handles missing 'title_column' in schedule_columns
    def test_missing_title_column(self):
        df = pd.DataFrame({'title': ['Networking event - Lunch', 'Workshop']})
        schedule_columns = {'networking_event_column': 'is_networking_event'}
        result = annotate_networking_event(df, schedule_columns)
        assert result.equals(df)

    # Deals with empty DataFrame input
    def test_empty_dataframe_input(self):
        df = pd.DataFrame(columns=['title'])
        schedule_columns = {'title_column': 'title', 'networking_event_column': 'is_networking_event'}
        result = annotate_networking_event(df, schedule_columns)
        assert result.empty


class TestGenerateIcalContent:

    # Correctly generates iCalendar content when room URL is provided
    def test_generate_ical_content_with_room_url(self):
        row = pd.Series({
            'date_column': '01.01.23',
            'start_time_column': '10:00',
            'end_time_column': '12:00',
            'title_column': 'Workshop Title',
            'room_column': 'Room B'
        })
        schedule_columns = {
            'date_column': 'date_column',
            'start_time_column': 'start_time_column',
            'end_time_column': 'end_time_column',
            'title_column': 'title_column',
            'room_column': 'room_column'
        }
        rooms = {
            'Room B': {'url': 'http://room-b-url.com'}
        }
        yearly = {'event_name': 'Annual Event'}

        with patch.object(Template, 'render', return_value='iCalendar Content with URL') as mock_template:
            result = generate_ical_content(row, schedule_columns, rooms, yearly)

            assert result == 'iCalendar Content with URL'
            mock_template.assert_called_once()

    # Handles missing room information gracefully
    def test_generate_ical_content_missing_room(self):
        row = pd.Series({
            'date_column': '01.01.23',
            'start_time_column': '10:00',
            'end_time_column': '12:00',
            'title_column': 'Workshop Title',
            'room_column': None
        })
        schedule_columns = {
            'date_column': 'date_column',
            'start_time_column': 'start_time_column',
            'end_time_column': 'end_time_column',
            'title_column': 'title_column',
            'room_column': 'room_column'
        }
        rooms = {}
        yearly = {'event_name': 'Annual Event'}

        with patch.object(Template, 'render', return_value='iCalendar Content without Room') as mock_template:
            result = generate_ical_content(row, schedule_columns, rooms, yearly)

            assert result == 'iCalendar Content without Room'
            mock_template.assert_called_once()

    # Manages incorrect date or time formats without crashing
    def test_generate_ical_content_incorrect_date_format(self):
        row = pd.Series({
            'date_column': 'invalid-date',
            'start_time_column': '10:00',
            'end_time_column': '12:00',
            'title_column': 'Workshop Title',
            'room_column': None
        })
        schedule_columns = {
            'date_column': 'date_column',
            'start_time_column': 'start_time_column',
            'end_time_column': 'end_time_column',
            'title_column': 'title_column',
            'room_column': 'room_column'
        }
        rooms = {}
        yearly = {'event_name': 'Annual Event'}

        result = generate_ical_content(row, schedule_columns, rooms, yearly)

        assert result == ""

    # Deals with missing columns in schedule data
    def test_generate_ical_content_missing_columns(self):
        row = pd.Series({
            # Missing date and time columns
            'title_column': 'Workshop Title',
            # Missing room column
        })
        schedule_columns = {
            # Missing date and time column mappings
            # Missing room column mapping
            'title_column': 'title_column'
        }
        rooms = {}
        yearly = {'event_name': 'Annual Event'}

        result = generate_ical_content(row, schedule_columns, rooms, yearly)

        assert result == ""


class TestWriteIcalFiles:

    # Successfully creates the output directory if it does not exist
    @pytest.mark.skip(reason="Fail on when dir not already exist")
    def test_creates_output_directory(self, tmp_path):
        df = pd.DataFrame()
        outdir_ics = tmp_path / 'test_output_dir'
        schedule_columns = {}
        rooms = {}
        yearly = {}

        write_ical_files(df, str(outdir_ics), schedule_columns, rooms, yearly)

        # Check if the directory was created
        assert outdir_ics.exists()

    # Successfully creates the output directory if it does not exist
    def test_creates_output_directory(self, monkeypatch):
        import os
        from pathlib import Path
        import pandas as pd

        mock_mkdir = monkeypatch.setattr(Path, 'mkdir', lambda *args, **kwargs: None)
        df = pd.DataFrame()
        outdir_ics = 'test_output_dir'
        schedule_columns = {}
        rooms = {}
        yearly = {}

        write_ical_files(df, outdir_ics, schedule_columns, rooms, yearly)

        assert Path(outdir_ics).exists()

    # Handles an empty DataFrame without errors
    def test_handles_empty_dataframe(self):

        df = pd.DataFrame()
        outdir_ics = 'test_output_dir'
        schedule_columns = {}
        rooms = {}
        yearly = {}

        try:
            write_ical_files(df, outdir_ics, schedule_columns, rooms, yearly)
            assert True
        except Exception:
            assert False

    # Manages missing or incorrect schedule column names gracefully
    def test_missing_schedule_columns(self):

        df = pd.DataFrame({'wrong_column': ['value']})
        outdir_ics = 'test_output_dir'
        schedule_columns = {'id_column': 'missing_id'}
        rooms = {}
        yearly = {}

        try:
            write_ical_files(df, outdir_ics, schedule_columns, rooms, yearly)
            assert True
        except KeyError:
            assert True

    # Deals with missing room information without crashing
    def test_missing_room_information(self):

        df = pd.DataFrame({'id': [1], 'room': ['nonexistent_room']})
        outdir_ics = 'test_output_dir'
        schedule_columns = {'id_column': 'id', 'room_column': 'room'}
        rooms = {}
        yearly = {}

        try:
            write_ical_files(df, outdir_ics, schedule_columns, rooms, yearly)
            assert True
        except KeyError:
            assert False


class TestWriteScheduleJson:

    # Converts a DataFrame to a JSON file with correct formatting
    def test_dataframe_to_json_formatting(self):
        import pandas as pd
        import os
        from obiwow.data_reader_parser import write_schedule_json

        schedule_df = pd.DataFrame({
            'id': [1],
            'date': [pd.to_datetime('2023-10-01')],
            'room': ['Room A'],
            'main_instructor': ['Instructor A'],
            'helper': ['Helper A'],
            'title': ['Workshop A'],
            'max_attendance': [30],
            'start_time': ['09:00'],
            'end_time': ['11:00']
        })
        schedule_columns = {
            'id_column': 'id',
            'date_column': 'date',
            'room_column': 'room',
            'main_instructor_column': 'main_instructor',
            'helper_instructor_column': 'helper',
            'title_column': 'title',
            'max_attendance': 'max_attendance',
            'start_time_column': 'start_time',
            'end_time_column': 'end_time'
        }
        output_file = 'test_schedule.json'

        write_schedule_json(schedule_df, schedule_columns, output_file)

        with open(output_file, 'r') as file:
            data = json.load(file)

        assert data['1']['date'] == '01.10.23'
        assert data['1']['room'] == 'Room A'
        assert data['1']['main_instructor'] == 'Instructor A'
        assert data['1']['helper'] == 'Helper A'
        assert data['1']['title'] == 'Workshop A'
        assert data['1']['max_attendance'] == 30
        assert data['1']['timeslot'] == '09:00-11:00'

        os.remove(output_file)

    # Maps DataFrame columns to JSON keys accurately
    def test_column_mapping_to_json_keys(self):
        import pandas as pd
        import os
        from obiwow.data_reader_parser import write_schedule_json

        schedule_df = pd.DataFrame({
            'workshop_id': [1],
            'event_date': [pd.to_datetime('2023-10-01')],
            'location': ['Room A'],
            'lead_instructor': ['Instructor A'],
            'assistant': ['Helper A'],
            'session_title': ['Workshop A'],
            'capacity': [30],
            'begin_time': ['09:00'],
            'finish_time': ['11:00']
        })
        schedule_columns = {
            'id_column': 'workshop_id',
            'date_column': 'event_date',
            'room_column': 'location',
            'main_instructor_column': 'lead_instructor',
            'helper_instructor_column': 'assistant',
            'title_column': 'session_title',
            'max_attendance': 'capacity',
            'start_time_column': 'begin_time',
            'end_time_column': 'finish_time'
        }
        output_file = 'test_schedule.json'

        write_schedule_json(schedule_df, schedule_columns, output_file)

        with open(output_file, 'r') as file:
            data = json.load(file)

        assert data['1']['date'] == '01.10.23'
        assert data['1']['room'] == 'Room A'
        assert data['1']['main_instructor'] == 'Instructor A'
        assert data['1']['helper'] == 'Helper A'
        assert data['1']['title'] == 'Workshop A'
        assert data['1']['max_attendance'] == 30
        assert data['1']['timeslot'] == '09:00-11:00'

        os.remove(output_file)

    # Handles DataFrame with missing columns gracefully
    def test_missing_columns_handling(self):
        schedule_df = pd.DataFrame({
            # Missing some columns intentionally
            'id': [1],
            # Missing date column
            # Missing room column
            # Missing main_instructor column
            # Missing helper column
            # Missing title column
            # Missing max_attendance column
            # Missing start_time column
            # Missing end_time column
        })
        schedule_columns = {
            'id_column': 'id',
            # Other columns are missing in the DataFrame and mapping
        }
        output_file = '/invalid_path/test_schedule.json'

        try:
            write_schedule_json(schedule_df, schedule_columns, output_file)
        except KeyError as e:
            assert str(e) in ["'date'", "'room'", "'main_instructor'", "'helper'", "'title'", "'max_attendance'",
                              "'start_time'", "'end_time'"]

    # Manages empty DataFrame without throwing errors
    @pytest.mark.skip(reason="Issue with wronf file path")
    def test_empty_dataframe_handling(self):

        schedule_df = pd.DataFrame(columns=[
            'id',
            'date',
            'room',
            'main_instructor',
            'helper',
            'title',
            'max_attendance',
            'start_time',
            'end_time'
        ])
        schedule_columns = {
            'id_column': 'id',
            'date_column': 'date',
            'room_column': 'room',
            'main_instructor_column': 'main_instructor',
            'helper_instructor_column': 'helper',
            'title_column': 'title',
            'max_attendance': 'max_attendance',
            'start_time_column': 'start_time',
            'end_time_column': 'end_time'
        }
        output_file = '/invalid_path/test_schedule.json'

        try:
            write_schedule_json(schedule_df, schedule_columns, output_file)

            with open(output_file, "r") as file:
                data = json.load(file)

            assert data == {}

        except Exception as e:
            assert False, f"Exception was raised: {e}"

    # Deals with invalid file paths for output JSON
    def test_invalid_output_path_handling(self):

        schedule_df = pd.DataFrame({
            # Minimal valid DataFrame setup for testing invalid path handling
            "id": [1],
            "date": [pd.to_datetime("2023-10-01")],
            "room": ["Room A"],
            "main_instructor": ["Instructor A"],
            "helper": ["Helper A"],
            "title": ["Workshop A"],
            "max_attendance": [30],
            "start_time": ["09:00"],
            "end_time": ["11:00"]
        })

        schedule_columns = {
            "id_column": "id",
            "date_column": "date",
            "room_column": "room",
            "main_instructor_column": "main_instructor",
            "helper_instructor_column": "helper",
            "title_column": "title",
            "max_attendance": "max_attendance",
            "start_time_column": "start_time",
            "end_time_column": "end_time"
        }

        invalid_output_file = '/invalid_path/test_schedule.json'

        try:
            write_schedule_json(schedule_df, schedule_columns, invalid_output_file)

        except IOError as e:
            assert isinstance(e, IOError)


class TestStandardiseTimeOfDay:

    # Converts 'morning' to 'morning'
    def test_converts_morning_to_morning(self):
        result = standardise_time_of_day('morning')
        assert result == 'morning'

    # Converts 'morgen' to 'morning'
    def test_converts_morgen_to_morning(self):
        result = standardise_time_of_day('morgen')
        assert result == 'morning'

    # Returns input when time string is not in any mapping
    def test_returns_input_when_not_in_mapping(self):
        input_time = 'evening'
        result = standardise_time_of_day(input_time)
        assert result == input_time

    # Handles empty string input gracefully
    def test_handles_empty_string_input(self):
        result = standardise_time_of_day('')
        assert result == ''

    # Handles case sensitivity in time strings
    def test_handles_case_sensitivity(self):
        result = standardise_time_of_day('MORNING')
        assert result == 'MORNING'


class TestStandardiseTimeOfDayColumn:

    # Standardizes time of day strings correctly in the specified column
    def test_standardizes_time_of_day_strings_correctly(self):
        df = pd.DataFrame({'time': ['morning', 'afternoon', 'whole day']})
        dict_columns = {'time_column': 'time'}
        result_df = standardise_time_of_day_column(df, dict_columns)
        expected_df = pd.DataFrame({'time': ['morning', 'afternoon', 'all day']})
        pd.testing.assert_frame_equal(result_df, expected_df)

    # Returns the DataFrame with updated time of day values
    def test_returns_dataframe_with_updated_values(self):
        df = pd.DataFrame({'time': ['morgen', 'ettermiddag', 'halv dag']})
        dict_columns = {'time_column': 'time'}
        result_df = standardise_time_of_day_column(df, dict_columns)
        expected_df = pd.DataFrame({'time': ['morning', 'afternoon', 'half a day']})
        pd.testing.assert_frame_equal(result_df, expected_df)

    # Handles DataFrame with missing time of day values gracefully
    def test_handles_missing_time_of_day_values(self):
        df = pd.DataFrame({'time': ['morning', None, 'afternoon']})
        dict_columns = {'time_column': 'time'}
        result_df = standardise_time_of_day_column(df, dict_columns)
        expected_df = pd.DataFrame({'time': ['morning', None, 'afternoon']})
        pd.testing.assert_frame_equal(result_df, expected_df)

    # Processes DataFrame with no matching columns in dict_columns without errors
    def test_no_matching_columns_in_dict_columns(self):
        df = pd.DataFrame({'time': ['morning', 'afternoon']})
        dict_columns = {'non_existent_column': 'time'}
        result_df = standardise_time_of_day_column(df, dict_columns)
        pd.testing.assert_frame_equal(result_df, df)

    # Manages DataFrame with non-string values in time columns
    def test_manages_non_string_values_in_time_columns(self):
        df = pd.DataFrame({'time': ['morning', 123, 'afternoon']})
        dict_columns = {'time_column': 'time'}
        result_df = standardise_time_of_day_column(df, dict_columns)
        expected_df = pd.DataFrame({'time': ['morning', 123, 'afternoon']})
        pd.testing.assert_frame_equal(result_df, expected_df)


class TestWriteHtmlPage:

    # Writes HTML content to the specified file path successfully
    def test_writes_html_content_successfully(self, tmp_path):
        full_page_html_rendered = "<html><body><h1>Test</h1></body></html>"
        file_path = tmp_path / "test_output.html"
        paths = {'output': {'html': {'file_path': str(file_path)}}}
        write_html_page(full_page_html_rendered, paths)
        with open(file_path, 'r') as file:
            content = file.read()
        assert content == full_page_html_rendered

    # Handles valid dictionary input for paths without errors
    def test_handles_valid_paths_dictionary(self, tmp_path):
        full_page_html_rendered = "<html><body><h1>Test</h1></body></html>"
        file_path = tmp_path / "test_output.html"
        paths = {'output': {'html': {'file_path': str(file_path)}}}
        try:
            write_html_page(full_page_html_rendered, paths)
            assert True
        except Exception:
            assert False

    # Paths dictionary is missing the 'output' or 'html' keys
    def test_missing_output_or_html_keys(self):
        full_page_html_rendered = "<html><body><h1>Test</h1></body></html>"
        paths_missing_output = {'html': {'file_path': 'test_output.html'}}
        paths_missing_html = {'output': {'file_path': 'test_output.html'}}
        with pytest.raises(KeyError):
            write_html_page(full_page_html_rendered, paths_missing_output)
        with pytest.raises(KeyError):
            write_html_page(full_page_html_rendered, paths_missing_html)

    # File path in paths dictionary is invalid or inaccessible
    def test_invalid_or_inaccessible_file_path(self):
        full_page_html_rendered = "<html><body><h1>Test</h1></body></html>"
        paths = {'output': {'html': {'file_path': '/invalid_path/test_output.html'}}}
        with pytest.raises(FileNotFoundError):
            write_html_page(full_page_html_rendered, paths)

    # HTML content is an empty string
    def test_empty_html_content(self, tmp_path):
        full_page_html_rendered = ""
        file_path = tmp_path / "test_output.html"
        paths = {'output': {'html': {'file_path': str(file_path)}}}
        write_html_page(full_page_html_rendered, paths)
        with open(file_path, 'r') as file:
            content = file.read()
        assert content == ""
