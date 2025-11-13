import pandas as pd
import yaml
from collections import defaultdict
import os

# Load rooms
with open("config/rooms.yaml", "r") as f:
    rooms_yaml = yaml.safe_load(f)

used_rooms = set()

# Read schedule CSV
schedule = pd.read_csv("inputs/schedule.csv")

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