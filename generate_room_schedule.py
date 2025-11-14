import pandas as pd
import yaml
from collections import defaultdict
import os

# Load rooms
with open("config/rooms.yaml", "r") as f:
    rooms_yaml = yaml.safe_load(f)

used_rooms = set()

# Read schedule from outputs/schedule.json instead of inputs/schedule.csv
import json

with open("outputs/schedule.json", "r") as f:
    schedule_data = json.load(f)

# Expand JSON to per-day per-room rows similar to the original CSV approach
rows = []
for workshop_id, w in schedule_data.items():
    # Unpack arrays
    dates = w.get("dates", [])
    timeslots = w.get("timeslots", [])
    rooms = w.get("rooms", [])
    n = max(len(dates), len(timeslots), len(rooms))
    # Pad arrays if necessary
    if not timeslots:
        timeslots = ["" for _ in range(len(dates))]
    if not rooms:
        rooms = ["" for _ in range(len(dates))]
    for i in range(n):
        rows.append({
            "Date": dates[i] if i < len(dates) else dates[0] if dates else "",
            "Time": timeslots[i] if i < len(timeslots) else timeslots[0] if timeslots else "",
            "Room in Ole Johan Dalshus": rooms[i] if i < len(rooms) else rooms[0] if rooms else "",
            "Workshop name": w.get("title", ""),
            "Main instructor": w.get("main_instructor", ""),
            "Helper": w.get("helper", ""),
            "Max attendance": w.get("max_attendance", ""),
            "ID": workshop_id
        })

schedule = pd.DataFrame(rows)

# Only keep rows with workshop names
workshop_rows = schedule[
    schedule["Workshop name"].notnull()
    & (schedule["Workshop name"] != "")
    & (schedule["Workshop name"].str.strip().str.lower() != "example")
]

# Determine all unique (day, time, room) combinations in schedule
all_days = sorted(workshop_rows["Date"].dropna().astype(str).unique().tolist())
all_times = sorted(workshop_rows["Time"].dropna().astype(str).unique().tolist())
all_rooms = sorted(workshop_rows["Room in Ole Johan Dalshus"].dropna().unique().tolist())

# Mark only rooms really used
rooms_in_use = sorted(set(r for r in all_rooms if isinstance(r, str) and r.strip()))

# Prep multidimensional structure: by (Day, Time, Room)
content = defaultdict(lambda: defaultdict(dict))
for _, row in workshop_rows.iterrows():
    day = row["Date"]
    time = row["Time"]
    room = row["Room in Ole Johan Dalshus"]
    name = row["Workshop name"]
    if not isinstance(room, str) or not room.strip():
        continue
    prev = content[(day, time)].get(room, "")
    if prev:
        prev += "<br>"
    content[(day, time)][room] = prev + name

# Write Markdown
outfile = "outputs/room_schedule.md"
os.makedirs(os.path.dirname(outfile), exist_ok=True)

with open(outfile, "w", encoding="utf-8") as f:
    # Header row with only used rooms
    header = ["Day", "Time"] + rooms_in_use
    f.write("| " + " | ".join(header) + " |\n")
    f.write("|" + "|".join(["---"] * len(header)) + "|\n")
    # Sort days as dates, times as custom order (morning < afternoon < full day)
    from datetime import datetime

    # Get all used (day, time) keys and sort
    def time_sort_key(t):
        # Custom order for time columns, now with 'full day' first
        order = {'full day': 0, 'morning': 1, 'afternoon': 2}
        return order.get(t[1].strip().lower(), 3), t[1].lower(), t[0]

    def date_key(d):
        try:
            return datetime.strptime(d, "%d.%m.%Y")
        except Exception:
            return d

    keys = list(content.keys())
    sorted_keys = sorted(keys, key=lambda x: (date_key(x[0]), time_sort_key(x)))
    for (day, time) in sorted_keys:
        row = [str(day), str(time)]
        for room in rooms_in_use:
            v = content[(day, time)].get(room, "")
            row.append(v)
        f.write("| " + " | ".join(row) + " |\n")
    
    # Write CSV as well
    import csv
    csv_outfile = "outputs/room_schedule.csv"
    with open(csv_outfile, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(["Day", "Time"] + rooms_in_use)
        for (day, time) in sorted_keys:
            row = [str(day), str(time)]
            for room in rooms_in_use:
                v = content[(day, time)].get(room, "")
                row.append(v)
            writer.writerow(row)
    
    print(f"Wrote table to {outfile}")
    print(f"Wrote CSV to {csv_outfile}")