* instead of `submission_title.tsv` as separate file,
  have correct nettskjema ID in schedule google sheet,
  so that it becomes part of `schedule.tsv`
  * also have code check for multiple entries for same workshop
* Maybe have these in a configuration file?
    * location of ical files
    * url of nettskjema for registration
* `tsv_to_html.py` should write out a list of workshop names and the shorthand (without spaces etc)
  that is used for the registration nettsjema.
  This can then be read by `registration_mail.py`
* Tackle `&` in workshop names for shorthand, currently it truncates at the `&`
