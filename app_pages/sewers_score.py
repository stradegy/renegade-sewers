import streamlit as st
import pandas as pd

st.title("Sewers Score")

# =========================================================
# LOAD FROM SESSION STATE
# =========================================================
if "df" not in st.session_state or st.session_state.df is None:
    st.error("sewers_score dataframe not found in session state.")
    st.stop()

source_df = st.session_state.df.copy()

if source_df.empty:
    st.warning("sewers_score dataframe is empty.")
    st.stop()

# =========================================================
# PREP / CLEAN
# source_df shape expected:
# IGN | 2026-06-03 | 2026-06-10 | ...
# =========================================================
df = source_df.copy()

# Identify raw date columns
raw_value_cols = [col for col in df.columns if col != "IGN"]

# Ensure numeric
for col in raw_value_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Dates sorted chronologically
date_columns = sorted(
    raw_value_cols,
    key=lambda x: pd.to_datetime(x, errors="coerce")
)

if len(date_columns) == 0:
    st.warning("No score date columns found.")
    st.stop()

# Store some shared values in session_state
st.session_state.names = sorted(df["IGN"].dropna().unique().tolist())
st.session_state.dates = date_columns
st.session_state.latest_date = date_columns[-1]
st.session_state.prev_date = date_columns[-2] if len(date_columns) >= 2 else None

# Rename date columns to *_total
new_date_columns = [f"{col}_total" for col in date_columns]
rename_map = dict(zip(date_columns, new_date_columns))
df = df.rename(columns=rename_map)

# Add delta columns
for i in range(1, len(new_date_columns)):
    prev_col = new_date_columns[i - 1]
    curr_col = new_date_columns[i]
    delta_col = curr_col.replace("_total", "_delta")
    df[delta_col] = df[curr_col] - df[prev_col]

# First delta defaults to 0
first_delta_col = f"{date_columns[0]}_delta"
df[first_delta_col] = 0

# Personal best
total_cols = [col for col in df.columns if col.endswith("_total")]
df["Personal Best"] = df[total_cols].max(axis=1, skipna=True)

# Date of personal best
date_of_personal_best = []
for _, row in df.iterrows():
    personal_best = row["Personal Best"]
    found_date = None

    if pd.notna(personal_best):
        for col in total_cols:
            if pd.notna(row[col]) and row[col] == personal_best:
                found_date = col.replace("_total", "")
                break

    date_of_personal_best.append(found_date)

df["Date of Personal Best"] = date_of_personal_best

# Theoretical high
st.session_state.theoretical_high = int(df["Personal Best"].fillna(0).sum())

# Weekly totals
st.session_state.weekly_totals = {}
for col in new_date_columns:
    date = col.replace("_total", "")
    st.session_state.weekly_totals[date] = df[col].fillna(0).sum()

# =========================================================
# SIDEBAR FILTERS
# Use page-specific session_state keys so they don't collide
# with future pages.
# =========================================================
st.sidebar.header("Sewers Score Filters")

if "sewer_selected_names" not in st.session_state:
    st.session_state.sewer_selected_names = st.session_state.names

if "sewer_selected_dates" not in st.session_state:
    st.session_state.sewer_selected_dates = st.session_state.dates

if "sewer_view_mode" not in st.session_state:
    st.session_state.sewer_view_mode = "Total"

if st.sidebar.button("Reset Selections", key="sewer_reset_button"):
    for key in ["sewer_selected_names", "sewer_selected_dates", "sewer_view_mode"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

selected_names = st.sidebar.multiselect(
    "Select Name(s)",
    options=st.session_state.names,
    default=st.session_state.sewer_selected_names,
    key="sewer_selected_names"
)

selected_dates = st.sidebar.multiselect(
    "Select Date(s)",
    options=st.session_state.dates,
    default=st.session_state.sewer_selected_dates,
    key="sewer_selected_dates"
)

view_mode = st.sidebar.radio(
    "Show",
    options=["Total", "Delta"],
    index=0 if st.session_state.sewer_view_mode == "Total" else 1,
    key="sewer_view_mode"
)

# Safety: always normalize as lists
if not isinstance(selected_names, list):
    selected_names = [selected_names] if selected_names else []

if not isinstance(selected_dates, list):
    selected_dates = [selected_dates] if selected_dates else []

if len(selected_names) == 0:
    st.warning("Please select at least one name.")
    st.stop()

if len(selected_dates) == 0:
    st.warning("Please select at least one date.")
    st.stop()

# =========================================================
# FILTERED VIEW
# =========================================================
filtered_df = df[df["IGN"].isin(selected_names)].copy()

date_total_columns = [f"{date}_total" for date in sorted(selected_dates)]
date_delta_columns = [f"{date}_delta" for date in sorted(selected_dates)]

view_columns = date_total_columns if view_mode == "Total" else date_delta_columns

display_df = filtered_df[["IGN", "Personal Best", "Date of Personal Best"] + view_columns].copy()

# Clean displayed column names back to bare dates
display_df = display_df.rename(columns=lambda col: col.replace("_total", "").replace("_delta", ""))

# =========================================================
# SUMMARY METRICS
# Show only when all names + all dates + Total
# =========================================================
all_names_selected = sorted(selected_names) == sorted(st.session_state.names)
all_dates_selected = sorted(selected_dates) == sorted(st.session_state.dates)

if all_names_selected and all_dates_selected and view_mode == "Total":
    col1, col2, col3 = st.columns(3)

    latest_date = st.session_state.latest_date
    prev_date = st.session_state.prev_date

    latest_total = st.session_state.weekly_totals.get(latest_date, 0)

    if prev_date is not None:
        prev_total = st.session_state.weekly_totals.get(prev_date, 0)
        delta = latest_total - prev_total
    else:
        delta = None

    with col1:
        st.metric(
            label="This week's total score",
            value=f"{int(latest_total):,}",
            delta=None if delta is None else f"{int(delta):,}"
        )

    with col2:
        latest_total_col = f"{latest_date}_total"
        pax = (df[latest_total_col].fillna(0) != 0).sum()
        st.metric(label="Pax Attempted", value=int(pax))

    with col3:
        st.metric(
            label="Theoretical highest total score",
            value=f"{int(st.session_state.theoretical_high):,}"
        )

# =========================================================
# SINGLE PLAYER METRIC
# =========================================================
if len(selected_names) == 1:
    player_name = selected_names[0]
    player_data = display_df[display_df["IGN"] == player_name]

    if not player_data.empty:
        personal_best = player_data["Personal Best"].iloc[0]
        date_pb = player_data["Date of Personal Best"].iloc[0]

        if pd.notna(personal_best):
            st.metric(
                "Personal Best",
                f"{int(personal_best):,}",
                delta=f"on {date_pb}" if pd.notna(date_pb) else None
            )

# =========================================================
# CHART
# =========================================================
chart_data = display_df.set_index("IGN")[selected_dates].T

if view_mode == "Total":
    st.subheader("Sewer Scores Over the Weeks")
else:
    st.subheader("Gains Over the Weeks")

st.line_chart(chart_data)

# =========================================================
# TABLE
# =========================================================
st.subheader("Tabular Data")
st.dataframe(display_df, use_container_width=True)