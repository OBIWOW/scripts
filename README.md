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
* `yearly_config.yaml` --> Variables that change each year, like the name of the events, the registration links, etc.

Except for `rooms.yaml`, you must not change the name the keys in the configuration files, only the values.

For the `rooms.yaml` file, you can add or remove rooms, but the structure must be the same.


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
2. Change the path to the downloaded file in the `paths.yaml` file (survey_results['file_path'] key). Delimiter can be set here.
3. To create the `submission_title.csv` file, run:

```
cut -d\; -f1,6 < survey_results.csv > submission_title.csv
```

4. If necessary, modify the `submission_title.csv` to remove any workshops that have withdrawn.
5. Go to the "Schedule" Google Sheet. Click on File > Download > Tab Separated Values (.tsv) and download a tsv of the spreadsheet.
6. Change the path to the downloaded file in the `paths.yaml` file (schedule['file_path'] key). Delimiter can be set here.
7. Run `python generate_website.py`

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
