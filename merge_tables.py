import csv
import pandas as pd

chars = pd.read_csv("data_raw/Characteristics.csv", encoding="utf-8-sig")
flow = pd.read_csv("data_raw/FlowStats.csv", encoding="utf-8-sig")
gws = pd.read_csv("data_raw/GlobalWatershed_Table.csv", encoding="utf-8-sig")

# Fix known entry error: "Tanwax_)1" → "Tanwax_01"
for df in (chars, flow, gws):
    df["Name"] = df["Name"].str.replace("Tanwax_)1", "Tanwax_01", regex=False)

# Deduplicate Characteristics by Name — AreaSqMi is the same for every row of a given watershed
chars_slim = chars[["Name", "AreaSqMi"]].drop_duplicates(subset="Name")

flow_slim = flow[["Name", "AreaSqMi", "StatName", "Value", "Units"]]

gws_slim = gws[["Name", "WarningMsg", "DRNAREA"]]

# Use FlowStats as the base (long format, one row per stat per watershed)
merged = (
    flow_slim
    .merge(chars_slim.rename(columns={"AreaSqMi": "AreaSqMi_Characteristics"}), on="Name", how="left")
    .merge(gws_slim, on="Name", how="left")
)

merged = merged[["Name", "AreaSqMi_Characteristics", "AreaSqMi", "StatName", "Value", "Units", "WarningMsg", "DRNAREA"]]
merged = merged.rename(columns={"AreaSqMi": "AreaSqMi_FlowStats", "Name": "Flood_ID"})

out_path = "streamstats_merged.csv"
merged.to_csv(out_path, index=False)
print(f"Wrote {len(merged)} rows to {out_path}")

# --- Wide-format StreamStats output (one row per watershed) ---

RETURN_INTERVALS = [
    ("2-yr",   "50-percent AEP flood"),
    ("5-yr",   "20-percent AEP flood"),
    ("10-yr",  "10-percent AEP flood"),
    ("25-yr",  "4-percent AEP flood"),
    ("50-yr",  "2-percent AEP flood"),
    ("100-yr", "1-percent AEP flood"),
    ("200-yr", "0.5-percent AEP flood"),
    ("500-yr", "0.2-percent AEP flood"),
]
stat_names = {stat for _, stat in RETURN_INTERVALS}

flow_wide = flow[flow["StatName"].isin(stat_names)][
    ["Name", "StatName", "Value", "PIl", "PIu", "SEp"]
].copy()
gws_wide = gws[["Name", "DRNAREA", "WarningMsg"]].drop_duplicates("Name")
flow_wide = flow_wide.merge(gws_wide, on="Name", how="left")

stat_to_ri = {stat: ri for ri, stat in RETURN_INTERVALS}
flow_wide["RI"] = flow_wide["StatName"].map(stat_to_ri)

header1 = ["Flood ID", "SS_DRNAREA"]
header2 = ["", ""]
for ri, stat in RETURN_INTERVALS:
    header1 += [ri, "", "", "", ""]
    header2 += [stat, "PIL", "PIU", "SEp", "SS_Warnings"]

data_rows = []
for name in sorted(flow_wide["Name"].unique()):
    ws = flow_wide[flow_wide["Name"] == name]
    drnarea = ws["DRNAREA"].iloc[0] if len(ws) else ""
    row = [name, drnarea]
    for ri, _ in RETURN_INTERVALS:
        ri_row = ws[ws["RI"] == ri]
        if len(ri_row):
            r = ri_row.iloc[0]
            row += [r["Value"], r["PIl"], r["PIu"], r["SEp"], r["WarningMsg"]]
        else:
            row += ["", "", "", "", ""]
    data_rows.append(row)

wide_path = "streamstats_wide.csv"
with open(wide_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header1)
    writer.writerow(header2)
    writer.writerows(data_rows)
print(f"Wrote {len(data_rows)} watersheds to {wide_path}")
