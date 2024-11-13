# Oslo Bioinformatics Workshop Week

Code for organising the annual Oslo Bioinformatics Workshop Week.

Scripts have variables that need to be updated each year.

## Generating the website for the workshop week

Script: `generate_website.py`

All changing variables are defined in the configuration files in the `config` folder.

### Overview of configuration files
* `nettskjema_columns.yaml` --> Column names in the nettskjema export.
* `paths.yaml` --> Paths to input files and output files. Delimiter can be set here.
* `rooms.yaml `--> Room names and MazeMap links
* `schedule_columns.yaml` --> Column names in the schedule export.
* `yearly_config.yaml` --> Variables that change each year, like the name of the events, the registration links, etc. This file should not be commited to the repository as it can contain sensitive information. Only the yearly_config.yaml.EXAMPLE should be commited.

Except for `rooms.yaml`, you must not change the name the keys in the configuration files, only the values.

For the `rooms.yaml` file, you can add or remove rooms, but the structure must be the same.

### Files needed and generated

Input:
* `survey_results` --> Exported files of the nettskjema with the proposals 
* `submission_title.csv`--> two column csv file with only nettskjema submission ID
   and workshop Title (Not used in the script, but useful for manual checks)
  * Sometimes folks resubmit their proposal, or proposals get withdrawn.
* `schedule` --> Export values of the schedule Google Sheet
* `footer.html` --> Footer display at the bottom of the schedule table

Output:
* `html` --> HTML file for adding to the website
* `schedule_json` --> JSON file with schedule
* Folder `ical` with calendar files to be added to Vortex

Example nettskjema: [2023 call for proposals](https://nettskjema.no/user/form/355618/view)

### Step-by-step

1. Go to the "Call for Workshop Proposals" Nettskjema. Click on "Se resultater." Under "Last ned svar", click "Last ned kommaseparert fil (.txt)"
2. Copy the example yearly configuration file

```shell
cp config/yearly_config.yaml.EXAMPLE config/yearly_config.yaml
```
3. Change the path to the downloaded file in the `paths.yaml` file (survey_results['file_path'] key). Delimiter can be set here.
4. To create the `submission_title.csv` file, run:

```shell
cut -d\; -f1,6 < survey_results.csv > submission_title.csv
```

5. If necessary, modify the `submission_title.csv` to remove any workshops that have withdrawn.
6. Go to the "Schedule" Google Sheet. Click on File > Download > Tab Separated Values (.tsv) and download a tsv of the spreadsheet.
7. Change the path to the downloaded file in the `paths.yaml` file (schedule['file_path'] key). Delimiter can be set here.
8. Run `python generate_website.py`

## Checking registrations

Script: `registrations.py`.

This script, a work in progress, uses the nettskjema API to check the number 
of registrations for each workshop and reports some statistics.

## Confirming registration

Script: `registration_mail.py`

Input:
* `registration_results.tsv` --> Tab Separated Values export of the nettskjema
   with the registrations
* `schedule.json` --> JSON file with schedule from `tsv2html.py`   
   

Output:
* `mail.tsv` --> File with the mail to send to the participants though the Google Sheet `00_send_mail_evaluation.gsheet`
* for each workshop, a file `registered.txt` --> File with the list of
  registered participants saved to the folder for that workshop
  to be shared with the instructors

## Evaluating the workshop

Script: `evaluation.py`

Input:
* `evaluation_results.tsv` --> Tab Separated Values export of the nettskjema
   with the evaluations
* `schedule.json` --> JSON file with schedule from `tsv2html.py`
* `OBiWoW_workshop_evaluation_report_content.qmd` --> a Quarto Markdown file
  with the content of the report, only missing the header

Output:
* for each workshop, `OBiWoW_workshop_evaluation_report.qmd`, a Quarto Markdown
  file with the yaml header information with workshop title,
  and a line that 'loads' the `OBiWoW_workshop_evaluation_report_content.qmd` file
* a report, `Evaluation_report.pdf` saved to the same folder for that workshop
  to be shared with the instructors
* `ObiWoW_workshop_evaluation_report_all_workshops.pdf` --> a report with responses 
  for all workshops combined

Note that quarto is needed for generating the report files.


## Modifying the Appearance of the Website

To modify the appearance of the website, you can edit the HTML templates used to generate the website. The templates are located in the `template` directory. The templates use the [Mako](https://www.makotemplates.org) templating engine, which allows for embedding Python code within HTML. Here are the steps to modify the templates:
Do NOT change the name or the path of those files.

1. **Locate the Templates**:
   - The main templates used are `workshop_body_template.html` and `schedule_table_template.html`.

2. **Edit the Templates**:
   - Open the template files in your preferred text editor or IDE.
   - Modify the HTML and CSS as needed to change the appearance of the website.
   - General style of the website can be modified between the <style></style> tags at the beginning of the template.
   - Specific styles for individual elements can be modified within the HTML tags.
   - Use the `${variable_name}` syntax to insert dynamic content into the templates.

3. **Example Modifications**:
   - **Change the Workshop Body Template**:
     - File: `template/workshop_body_template.html`
     - Example: To change the header style of each workshop, you can modify the `<h2>` tag.
     ```html
     <hr class="double">
     <div id="${workshop_number}">
         <h2 style="color: blue;">${workshop_title}</h2>
         <!-- Add your custom styles here -->
     </div>
     ```

   - **Change the Schedule Table Template**:
     - File: `template/schedule_table_template.html`
     - Example: To change the table header background color, you can modify the CSS in the `<style>` section.
     ```html
     <style>
         #table_sched th {
             background-color: #4CAF50; /* Change to your desired color */
             text-align: center;
         }
         /* Add your custom styles here */
     </style>
     ```

4. **Save and Regenerate**:
   - After making your changes, save the template files.
   - Run the `generate_website.py` script to regenerate the HTML files with the updated templates.
   ```shell
   python generate_website.py
   ```

5. **Review Changes**:
   - Open the generated HTML file specified in the `paths.yaml` configuration file to review your changes.

By following these steps, you can customize the appearance of the website to match your desired style.

### Modifying the template further
Variable aceessible on the template are defined in the `tsv_to_html.py` script. `workshop_body_template.html` is called in the `generate_workshop_body` function and `schedule_table_template.html` is called in the generate_schedule_table function respective in the `tsv_to_html.py` script.


### Notes on the Mako template synthax
Further information can be found in the [Mako documentation](https://docs.makotemplates.org/en/latest/syntax.html). Here are some key points:
#### **Variable Substitution:**
Use `${variable_name}` to insert the value of a variable into the HTML.

The variable name should match the key in the dictionary passed to the template. Operation are possible within the curly brackets.

Example:
```html
<h1>${title.upper()}</h1>
```

#### **Control Structures:**

Use `%` for control structures like loops and conditionals.

Since there is no indentation in the template, the control structure end must be defined `%` key word. Here is a table of the control structures with their beginning and end synthax:

| Control structure | Beginning                 | End        |
|-------------------|---------------------------|------------|
| if                | `% if condition:`         | `% endif`  |
| for               | `% for item in in items:` | `% endfor` |

Example of a for loop with a conditional statement:
```html
% for workshop in workshops:
    % if workshop['registered'] > 0:
        <p>${workshop['title']} has ${workshop['registered']} registered participants.</p>
    % endif
% endfor
```

#### Python code blocks: 
Use `<% %>` tags to embed Python code blocks within the template.

Example:
```html
<% 
    def list_remaining_spaces(workshop):
        return workshop['max_participants'] - workshop['registered']

    remaining_spaces = list_remaining_spaces(workshop)
%>

<p>Remaining spaces: ${remaining_spaces}</p>
```
The function can be called with `${function_name()}` outside the block.

