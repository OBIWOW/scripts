# Oslo Bioinformatics Workshop Week

Code for organising the annual Oslo Bioinformatics Workshop Week.

Scripts have variables that need to be updated each year.

## Generating the website for the workshop week

Script: `tsv2html.py`

Input:
* `survey_results.csv` --> Semi-colon Separated Values export of the nettskjema
   with the proposals
* `submission_title.csv`--> two column csv file with only nettskjema submission ID
   and workshop Title
  * Sometimes folks resubmit their proposal, or proposals get withdrawn.
* `schedule.tsv` --> Tab Separated Values export of the schedule Google Sheet
* `footer.html` --> 

Output:
* `workshop_content.html` --> HTML file for adding to the website
* `schedule.json` --> JSON file with schedule
* Folder `ical` with calendar files to be added to Vortex

Example nettskjema: [2023 call for proposals](https://nettskjema.no/user/form/355618/view)

### Step-by-step

1. Go to the "Call for Workshop Proposals" Nettskjema. Click on "Se resultater." Under "Last ned svar", click "Last ned kommaseparert fil (.txt)"
2. Rename the resulting file to `survey_results.csv` and move it to the OBiWoW code directory.
3. To create the `submission_title.csv` file, run:

```
cut -d\; -f1,6 < survey_results.csv > submission_title.csv
```

4. If necessary, modify the `submission_title.csv` to remove any workshops that have withdrawn.
5. Go to the "Schedule" Google Sheet. Click on File > Download > Tab Separated Values (.tsv) and download a tsv of the spreadsheet.
6. Rename the resulting file to `schedule.tsv` and move it to the OBiWoW code directory.
7. Run `python tsv2html.py`

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
