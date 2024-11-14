import pytest
import pandas as pd
from unittest.mock import patch

from obiwow.tsv_to_html import room_info, make_list, generate_workshop_body, generate_schedule_table, \
    generate_full_html_page


class TestRoomInfo:

    # Returns correct room name and URL when room information is available
    def test_returns_correct_room_name_and_url(self):
        data = pd.Series({'room_column': 'Room A'})
        dict_room = {'Room A': {'url': 'http://room-a-url.com'}}
        schedule_columns = {'room_column': 'room_column'}
        room_name, room_url = room_info(data, dict_room, schedule_columns)
        assert room_name == 'Room A'
        assert room_url == 'http://room-a-url.com'

    # Handles valid schedule data input correctly
    def test_handles_valid_schedule_data(self):
        data = pd.Series({'room_column': 'Room B'})
        dict_room = {'Room B': {'url': 'http://room-b-url.com'}}
        schedule_columns = {'room_column': 'room_column'}
        room_name, room_url = room_info(data, dict_room, schedule_columns)
        assert room_name == 'Room B'
        assert room_url == 'http://room-b-url.com'

    # Handles missing room information by returning default message
    def test_handles_missing_room_information(self):
        data = pd.Series({'room_column': 'Room C'})
        dict_room = {}
        schedule_columns = {'room_column': 'room_column'}
        room_name, room_url = room_info(data, dict_room, schedule_columns)
        assert room_name == 'Room C'
        assert room_url is None

    # Manages KeyError when room name is not found in dict_room
    def test_manages_keyerror_for_missing_room_name(self):
        data = pd.Series({'room_column': 'Room D'})
        dict_room = {'Room E': {'url': 'http://room-e-url.com'}}
        schedule_columns = {'room_column': 'room_column'}
        room_name, room_url = room_info(data, dict_room, schedule_columns)
        assert room_name == 'Room D'
        assert room_url is None

    # Deals with 'nan' values in room_column gracefully
    def test_deals_with_nan_values_in_room_column(self):
        data = pd.Series({'room_column': float('nan')})
        dict_room = {}
        schedule_columns = {'room_column': 'room_column'}
        room_name, room_url = room_info(data, dict_room, schedule_columns)
        assert room_name == "No room information available"
        assert room_url is None


class TestMakeList:

    # Correctly splits strings with numbered lists into separate elements
    def test_splits_numbered_lists(self):
        result, has_header = make_list("1. First item\n2. Second item\n3. Third item")
        assert result == ["First item", "Second item", "Third item"]
        assert not has_header

    # Correctly identifies and processes strings with bullet points
    def test_processes_bullet_points(self):
        result, has_header = make_list("• First bullet\n• Second bullet\n• Third bullet")
        assert result == ["First bullet", "Second bullet", "Third bullet"]
        assert not has_header

    # Correctly identifies and processes strings with bullet points
    def test_processes_star(self):
        result, has_header = make_list("* First bullet\n* Second bullet\n* Third bullet")
        assert result == ["First bullet", "Second bullet", "Third bullet"]
        assert not has_header

    # Correctly identifies and processes strings with dashes
    def test_numbers_followed_by_dash(self):
        result, has_header = make_list("1- First item\n2- Second item\n3- Third item")
        assert result == ["First item", "Second item", "Third item"]
        assert not has_header

    #
    def test_dash_followed_by_space(self):
        result, has_header = make_list("1- First item\n2- Second item\n3- Third item")
        assert result == ["First item", "Second item", "Third item"]
        assert not has_header

    # Handles strings without any bullet points, dashes, or numbers
    def test_handles_no_bullets_or_numbers(self):
        result, has_header = make_list("Just a simple string without bullets or numbers")
        assert result == ["Just a simple string without bullets or numbers"]
        assert not has_header

    # Processes strings with numbers not followed by a period correctly
    def test_numbers_not_followed_by_period(self):
        result, has_header = make_list("1 First item\n2 Second item\n3 Third item")
        assert result == ["1 First item\n2 Second item\n3 Third item"]
        assert not has_header

    # Manages strings with multiple headers or colons
    def test_multiple_headers_or_colons(self):
        result, has_header = make_list("Header1: Item1\nHeader2: Item2\nHeader3: Item3")
        assert result == ["Header1: Item1\nHeader2: Item2\nHeader3: Item3"]
        assert not has_header

    # Correctly identifies and processes strings with headers
    def test_processes_strings_with_headers(self):
        result, has_header = make_list("Header1: 1- Item1\n2- Item2\n3- Item3")
        assert result == ["Header1:", "Item1", "Item2", "Item3"]
        assert has_header


class TestGenerateWorkshopBody:
    expected_html = ('<hr class="double">\n'
                     '<div id="1">\n'
                     '    <h2>Workshop Title</h2>\n'
                     '    <p>\n'
                     '        <strong><u>Date</u>: Sunday 01 January 2023 9:00-12:00 '
                     '13:00-16:00</strong>\n'
                     '        <a rel="noreferrer noopener" target="_blank" href="/ics/1.ics">Add '
                     'to calendar</a>\n'
                     '    </p>\n'
                     '    <strong><u>Room</u>:</strong>\n'
                     '        Room A\n'
                     '    <p>\n'
                     '            <a  rel="noreferrer noopener" target="_blank" '
                     'href="/register/Workshop_Title/end/">Register here</a>\n'
                     '    </p>\n'
                     '    <h4>Description</h4>\n'
                     '    <p align="justify">\n'
                     '        Workshop Description\n'
                     '    </p>\n'
                     '    <div style="background-color:#b6efed;width:90%;border-radius: '
                     '15px;padding: 10px;margin-left: auto;margin-right: auto;">\n'
                     '        <p>\n'
                     '            <h4>Learning outcomes</h4>\n'
                     '                <ul>\n'
                     '                    <li>Learning Outcomes</li>\n'
                     '                </ul>\n'
                     '        </p>\n'
                     '        <br>\n'
                     '    </div>\n'
                     '    <h3>Target audience</h3>\n'
                     '    <p>Target Audience</p>\n'
                     '</div>\n'
                     '<h3>Pre-requisites</h3>\n'
                     '<p>\n'
                     '            <ul>\n'
                     '                <li>Prerequisites</li>\n'
                     '            </ul>\n'
                     '</p>\n'
                     '<h3>Equipment to bring</h3>\n'
                     '<p>\n'
                     '    Materials\n'
                     '</p>\n'
                     '<p>\n'
                     '    <strong>Instructor(s):<br></strong>Instructor (main)<br>\n'
                     '        Helper\n'
                     '</p>\n'
                     '<a href="#table_sched">Go back</a>')

    # Generates HTML sections for each workshop using Mako template
    def test_generate_html_sections(self):
        # with patch('mako.template.Template.render', return_value='<html></html>') as mock_template:
        submission_schedule_df = pd.DataFrame({
            'networking_event_column': [False],
            'ID': [1],
            'Date': ['01.01.23'],
            'start_time_column': ['9:00'],
            'end_time_column': ['16:00'],
            'Main instructor': ['Instructor'],
            'Helper': ['Helper'],
            'Title': ['Workshop Title'],
            'Room': ['Room A'],
            'Description': ['Workshop Description'],
            'Outcome': ['Learning Outcomes'],
            'Target': ['Target Audience'],
            'PreReq': ['Prerequisites'],
            'Material': ['Materials']
        })
        nettskjema_columns = {'title_column': 'Title', 'description_column': 'Description',
                              'outcome_column': 'Outcome', 'target_column': 'Target',
                              'pre_requisite_column': 'PreReq', 'material_column': 'Material'}
        schedule_columns = {'networking_event_column': 'networking_event_column',
                            'id_column': 'ID', 'date_column': 'Date',
                            'start_time_column': 'start_time_column', 'end_time_column': 'end_time_column',
                            'main_instructor_column': 'Main instructor',
                            'helper_instructor_column': 'Helper', 'room_column': 'Room'}
        yearly = {'ics_folder': '/ics/', 'registration_open': True,
                  'pre_register_link': '/register/', 'post_register_link': '/end/'}
        rooms = {}
        result = generate_workshop_body(submission_schedule_df, nettskjema_columns, schedule_columns, yearly, rooms)
        assert len(result) == 1
        assert result[0] == self.expected_html

    # Correctly formats workshop date and time, including special time formatting
    def test_format_workshop_date_and_time(self):
        submission_schedule_df = pd.DataFrame({
            'networking_event_column': [False],
            'ID': [1],
            'Date': ['01.01.23'],
            'start_time_column': ['9:00'],
            'end_time_column': ['16:00'],
            'Main instructor': ['Instructor'],
            'Helper': ['Helper'],
            'Title': ['Workshop Title'],
            'Room': ['Room A'],
            'Description': ['Workshop Description'],
            'Outcome': ['Learning Outcomes'],
            'Target': ['Target Audience'],
            'PreReq': ['Prerequisites'],
            'Material': ['Materials']
        })
        nettskjema_columns = {'title_column': 'Title', 'description_column': 'Description',
                              'outcome_column': 'Outcome', 'target_column': 'Target',
                              'pre_requisite_column': 'PreReq', 'material_column': 'Material'}
        schedule_columns = {'networking_event_column': 'networking_event_column',
                            'id_column': 'ID', 'date_column': 'Date',
                            'start_time_column': 'start_time_column', 'end_time_column': 'end_time_column',
                            'main_instructor_column': 'Main instructor',
                            'helper_instructor_column': 'Helper', 'room_column': 'Room'}
        yearly = {'ics_folder': '/ics/', 'registration_open': True,
                  'pre_register_link': '/register/', 'post_register_link': '/end/'}
        rooms = {}
        result = generate_workshop_body(submission_schedule_df, nettskjema_columns, schedule_columns, yearly, rooms)
        assert "Sunday 01 January 2023" in result[0]
        assert "9:00-12:00 13:00-16:00" in result[0]

    # Handles missing or incorrect room information gracefully
    def test_handle_missing_room_info(self):
        submission_schedule_df = pd.DataFrame({
            'networking_event_column': [False],
            'ID': [1],
            'Date': ['01.01.23'],
            'start_time_column': ['9:00'],
            'end_time_column': ['16:00'],
            'Main instructor': ['Instructor'],
            'Helper': ['Helper'],
            'Title': ['Workshop Title'],
            'Room': ['nan'],
            'Description': ['Workshop Description'],
            'Outcome': ['Learning Outcomes'],
            'Target': ['Target Audience'],
            'PreReq': ['Prerequisites'],
            'Material': ['Materials']
        })
        nettskjema_columns = {'title_column': 'Title', 'description_column': 'Description',
                              'outcome_column': 'Outcome', 'target_column': 'Target',
                              'pre_requisite_column': 'PreReq', 'material_column': 'Material'}
        schedule_columns = {'networking_event_column': 'networking_event_column',
                            'id_column': 'ID', 'date_column': 'Date',
                            'start_time_column': 'start_time_column', 'end_time_column': 'end_time_column',
                            'main_instructor_column': 'Main instructor',
                            'helper_instructor_column': 'Helper', 'room_column': 'Room'}
        yearly = {'ics_folder': '/ics/', 'registration_open': True,
                  'pre_register_link': '/register/', 'post_register_link': '/end/'}
        rooms = {}
        result = generate_workshop_body(submission_schedule_df, nettskjema_columns, schedule_columns, yearly, rooms)
        assert "No room information available" in result[0]

    # Manages empty or malformed schedule data
    def test_manage_empty_schedule_data(self):
        submission_schedule_df = pd.DataFrame(columns=['networking_event_column',
                                                       'id_column',
                                                       'date_column',
                                                       'start_time_column',
                                                       'end_time_column',
                                                       'main_instructor_column',
                                                       'helper_instructor_column'])
        nettskjema_columns = {'title_column': '',
                              'description_column': '',
                              'outcome_column': '',
                              'target_column': '',
                              'pre_requisite_column': '',
                              'material_column': ''}
        schedule_columns = {'networking_event_column': '',
                            'id_column': '',
                            'date_column': '',
                            'start_time_column': '',
                            'end_time_column': '',
                            'main_instructor_column': '',
                            'helper_instructor_column': ''}
        yearly = {'ics_folder': '',
                  'registration_open': False,
                  'pre_register_link': '',
                  'post_register_link': ''}
        rooms = {}
        result = generate_workshop_body(submission_schedule_df, nettskjema_columns, schedule_columns, yearly, rooms)
        assert result == []

    # Processes workshops with no learning outcomes or prerequisites
    def test_no_learning_outcomes_or_prerequisites(self):
        submission_schedule_df = pd.DataFrame({
            "networking_event_column": [False],
            "ID": [1],
            "Date": ["01.01.23"],
            "start_time_column": ["9:00"],
            "end_time_column": ["16:00"],
            'Main instructor': ['Instructor'],
            'Helper': ['Helper'],
            'Title': ['Workshop Title'],
            'Room': ['Room A'],
            'Description': ['Workshop Description'],
            'Outcome': ['Learning Outcomes'],
            'Target': ['Target Audience'],
            'PreReq': ['Prerequisites'],
            'Material': ['Materials'],

        })
        nettskjema_columns = {
            "title_column": "Title",
            "description_column": "Description",
            "outcome_column": "Outcome",
            "target_column": "Target",
            "pre_requisite_column": "PreReq",
            "material_column": "Material"
        }
        schedule_columns = {'networking_event_column': 'networking_event_column',
                            'id_column': 'ID', 'date_column': 'Date',
                            'start_time_column': 'start_time_column', 'end_time_column': 'end_time_column',
                            'main_instructor_column': 'Main instructor',
                            'helper_instructor_column': 'Helper', 'room_column': 'Room'}
        yearly = {
            "ics_folder": "/ics/",
            "registration_open": True,
            "pre_register_link": "/register/",
            "post_register_link": "/end/"
        }
        rooms = {}
        result = generate_workshop_body(submission_schedule_df, nettskjema_columns, schedule_columns, yearly, rooms)
        assert '<ul>\n                <li>Prerequisites</li>\n            </ul>\n' in result[0] and \
               ('<h4>Learning outcomes</h4>\n                <ul>\n                    <li>Learning Outcomes</li>\n   '
                '             </ul>\n') in result[0]



class TestGenerateScheduleTable:

    # Converts 'Date' column to datetime objects successfully
    def test_convert_date_column_to_datetime(self, mocker):
        data = {'Date': ['01.01.21', '02.01.21'], 'Event': ['Event1', 'Event2']}
        schedule_df = pd.DataFrame(data)
        schedule_columns = {'Date': 'Date', 'Event': 'Event'}
        yearly = {'networking_event_url': 'http://example.com'}

        mocker.patch('obiwow.tsv_to_html.Template.render', return_value='rendered_html')

        result = generate_schedule_table(schedule_df, schedule_columns, yearly)

        assert 'rendered_html' in result

    # Sorts DataFrame by 'Date' column correctly
    def test_sort_dataframe_by_date(self, mocker):
        data = {'Date': ['02.01.21', '01.01.21'], 'Event': ['Event2', 'Event1']}
        schedule_df = pd.DataFrame(data)
        schedule_columns = {'Date': 'Date', 'Event': 'Event'}
        yearly = {'networking_event_url': 'http://example.com'}

        mocker.patch('obiwow.tsv_to_html.Template.render', return_value='rendered_html')

        result = generate_schedule_table(schedule_df, schedule_columns, yearly)

        assert 'rendered_html' in result

    # Handles empty DataFrame without crashing
    def test_handle_empty_dataframe(self, mocker):
        schedule_df = pd.DataFrame(columns=['Date', 'Event'])
        schedule_columns = {'Date': 'Date', 'Event': 'Event'}
        yearly = {'networking_event_url': 'http://example.com'}

        mocker.patch('obiwow.tsv_to_html.Template.render', return_value='rendered_html')

        result = generate_schedule_table(schedule_df, schedule_columns, yearly)

        assert 'rendered_html' in result

    # Manages missing 'Date' column gracefully
    def test_missing_date_column(self, mocker):
        data = {'Event': ['Event1', 'Event2']}
        schedule_df = pd.DataFrame(data)
        schedule_columns = {'Date': 'Date', 'Event': 'Event'}
        yearly = {'networking_event_url': 'http://example.com'}

        mocker.patch('obiwow.tsv_to_html.Template.render', return_value='rendered_html')

        try:
            generate_schedule_table(schedule_df, schedule_columns, yearly)
            assert False, "Expected an exception due to missing 'Date' column"
        except KeyError:
            pass

    # Deals with invalid date formats in 'Date' column
    def test_invalid_date_format(self, mocker):
        data = {'Date': ['invalid_date', '01.01.21'], 'Event': ['Event1', 'Event2']}
        schedule_df = pd.DataFrame(data)
        schedule_columns = {'Date': 'Date', 'Event': 'Event'}
        yearly = {'networking_event_url': 'http://example.com'}

        mocker.patch('obiwow.tsv_to_html.Template.render', return_value='rendered_html')

        try:
            generate_schedule_table(schedule_df, schedule_columns, yearly)
            assert False, "Expected an exception due to invalid date format"
        except ValueError:
            pass


class TestGenerateFullHtmlPage:

    # Generates full HTML page with valid inputs
    def test_generate_full_html_page_with_valid_inputs(self, mocker):
        mocker.patch('mako.template.Template.render', return_value='<html></html>')
        schedule_table_html = "<table><tr><td>Schedule</td></tr></table>"
        workshop_body_html = ["<div>Workshop 1</div>", "<div>Workshop 2</div>"]
        yearly = {'event_name': 'Annual Event'}
        result = generate_full_html_page(schedule_table_html, workshop_body_html, yearly)
        assert '<html></html>' in result

    # Correctly renders header and footer templates in the generated HTML page
    def test_renders_header_and_footer_templates(self, mocker):
        header_render_mock = mocker.patch('mako.template.Template.render', side_effect=['<header></header>', '<footer></footer>'])
        schedule_table_html = "<table><tr><td>Schedule</td></tr></table>"
        workshop_body_html = ["<div>Workshop 1</div>", "<div>Workshop 2</div>"]
        yearly = {'event_name': 'Annual Event'}
        result = generate_full_html_page(schedule_table_html, workshop_body_html, yearly)
        assert '<header></header>' in result
        assert '<footer></footer>' in result
        assert result.startswith('<header></header>')
        assert result.endswith('<footer></footer>')
        header_render_mock.assert_any_call()

    # Handles missing or empty schedule_table_html gracefully
    def test_handles_empty_schedule_table_html(self, mocker):
        mocker.patch('mako.template.Template.render', return_value='<html></html>')
        schedule_table_html = ""
        workshop_body_html = ["<div>Workshop 1</div>", "<div>Workshop 2</div>"]
        yearly = {'event_name': 'Annual Event'}
        result = generate_full_html_page(schedule_table_html, workshop_body_html, yearly)
        assert '<html></html>' in result

    # Manages empty workshop_body_html list without errors
    def test_manages_empty_workshop_body_html(self, mocker):
        mocker.patch('mako.template.Template.render', return_value='<html></html>')
        schedule_table_html = "<table><tr><td>Schedule</td></tr></table>"
        workshop_body_html = []
        yearly = {'event_name': 'Annual Event'}
        result = generate_full_html_page(schedule_table_html, workshop_body_html, yearly)
        assert '<html></html>' in result

    # Deals with missing keys in yearly dictionary
    def test_missing_keys_in_yearly_dict(self, mocker):
        mocker.patch('mako.template.Template.render', return_value='<html></html>')
        schedule_table_html = "<table><tr><td>Schedule</td></tr></table>"
        workshop_body_html = ["<div>Workshop 1</div>", "<div>Workshop 2</div>"]
        yearly = {}
        with pytest.raises(KeyError):
            generate_full_html_page(schedule_table_html, workshop_body_html, yearly)