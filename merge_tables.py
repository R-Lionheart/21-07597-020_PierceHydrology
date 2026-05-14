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
merged = merged.rename(columns={"AreaSqMi": "AreaSqMi_FlowStats"})

out_path = "table2_combined.csv"
merged.to_csv(out_path, index=False)
print(f"Wrote {len(merged)} rows to {out_path}")
print(merged.head())
