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
print(merged.head())

# --- Join streamstats with Table2 discharge summary ---

table2 = pd.read_excel("data_raw/Table2_summary_of_discharges.xlsx")

# Keep only the relevant Table2 columns
aep_cols = [c for c in table2.columns if "Annual-Chance" in c]
table2_slim = table2[
    ["Flood_ID", "Flooding Source", "Location", "Drainage Area (square miles)"] + aep_cols
]

# Melt AEP discharge columns to long format
table2_long = table2_slim.melt(
    id_vars=["Flood_ID", "Flooding Source", "Location", "Drainage Area (square miles)"],
    var_name="Table2_Label",
    value_name="Table2_cfs",
)

# Map Table2 column labels to StreamStats StatName for joining;
# "1-Percent Plus Annual-Chance" has no direct SS equivalent and maps to NaN
label_to_statname = {
    "0.2-Percent-Annual-Chance (cfs)": "0.2-percent AEP flood",
    "1-Percent-Annual-Chance (cfs)":   "1-percent AEP flood",
    "2-Percent-Annual-Chance (cfs)":   "2-percent AEP flood",
    "4-Percent-Annual-Chance (cfs)":   "4-percent AEP flood",
    "10-Percent-Annual-Chance (cfs)":  "10-percent AEP flood",
}
table2_long["StatName"] = table2_long["Table2_Label"].map(label_to_statname)

# Outer join preserves all AEP rows from both sources;
# Table2-only rows (1-Percent Plus) and SS-only rows (0.5%, 20%, 50%) get NaN in unmatched columns
combined = table2_long.merge(
    merged,
    on=["Flood_ID", "StatName"],
    how="outer",
)

out_path2 = "table2_streamstats_merged.csv"
combined.to_csv(out_path2, index=False)
print(f"Wrote {len(combined)} rows to {out_path2}")
