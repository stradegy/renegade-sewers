import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from io import BytesIO

st.title("Cumulative Score")

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
# IDENTIFY DATE COLUMNS
# Expected shape:
# IGN | 2026-06-03 | 2026-06-10 | ...
# =========================================================
date_columns = [col for col in source_df.columns if col != "IGN"]

if not date_columns:
    st.warning("No score date columns found.")
    st.stop()

date_columns = sorted(date_columns, key=lambda x: pd.to_datetime(x, errors="coerce"))
latest_date = date_columns[-1]

# =========================================================
# SIDEBAR CONTROLS
# =========================================================
st.sidebar.header("Cumulative Score Filters")

selected_dates = st.sidebar.multiselect(
    "Select date(s)",
    options=date_columns,
    default=[latest_date]
)

exclude_zero = st.sidebar.checkbox("Exclude zero scorers", value=True)

query_mode = st.sidebar.radio(
    "Query mode",
    options=["%", "Pax"],
    index=0,
    horizontal=True
)

if query_mode == "%":
    query_value = st.sidebar.slider(
        "Target %",
        min_value=1,
        max_value=100,
        value=50,
        step=1
    )
else:
    query_value = st.sidebar.slider(
        "Top X Pax",
        min_value=1,
        max_value=200,
        value=10,
        step=1
    )

if not selected_dates:
    st.warning("Please select at least one date.")
    st.stop()

# =========================================================
# HELPERS
# =========================================================
def fmt_int(x):
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)

def prepare_cumulative_for_date(df: pd.DataFrame, date_col: str, exclude_zero: bool = True) -> pd.DataFrame:
    temp = df[["IGN", date_col]].copy()
    temp = temp.rename(columns={date_col: "Score"})
    temp["Score"] = pd.to_numeric(temp["Score"], errors="coerce").fillna(0)

    if exclude_zero:
        temp = temp[temp["Score"] > 0].copy()

    temp = temp.sort_values("Score", ascending=False).reset_index(drop=True)

    if temp.empty:
        temp["Rank"] = []
        temp["Cumulative Score"] = []
        temp["Cumulative % of Total"] = []
        return temp

    temp["Rank"] = range(1, len(temp) + 1)
    temp["Cumulative Score"] = temp["Score"].cumsum()

    total_score = temp["Score"].sum()
    if total_score == 0:
        temp["Cumulative % of Total"] = 0.0
    else:
        temp["Cumulative % of Total"] = temp["Cumulative Score"] / total_score * 100

    temp["Date"] = date_col
    temp["Total Score"] = total_score
    return temp

def get_pct_threshold_result(cum_df: pd.DataFrame, threshold_pct: float):
    hit = cum_df[cum_df["Cumulative % of Total"] >= threshold_pct]
    if hit.empty:
        return None
    row = hit.iloc[0]
    return {
        "Date": row["Date"],
        "Target %": threshold_pct,
        "People Needed": int(row["Rank"]),
        "Cumulative Score": int(row["Cumulative Score"]),
        "Actual Cumulative %": float(row["Cumulative % of Total"]),
        "Total Score": int(row["Total Score"]),
    }

def get_pax_result(cum_df: pd.DataFrame, pax_count: int):
    if cum_df.empty:
        return None

    pax_count = min(int(pax_count), len(cum_df))
    row = cum_df.iloc[pax_count - 1]

    return {
        "Date": row["Date"],
        "Top X Pax": pax_count,
        "Cumulative Score": int(row["Cumulative Score"]),
        "Cumulative % of Total": float(row["Cumulative % of Total"]),
        "Total Score": int(row["Total Score"]),
    }

def fig_to_png_bytes(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    png_bytes = buf.getvalue()
    plt.close(fig)
    return png_bytes

@st.cache_data(show_spinner=False)
def render_cumulative_chart(chart_input: pd.DataFrame) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    fig.patch.set_facecolor("#eeeeee")
    ax.set_facecolor("#eeeeee")

    if chart_input.empty:
        ax.set_title("Cumulative Contribution Curve")
        ax.set_xlabel("No. of Pax")
        ax.set_ylabel("% of Sewer Score")
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
        return fig_to_png_bytes(fig)

    for date_label in chart_input["Date"].dropna().unique():
        g = chart_input[chart_input["Date"] == date_label].sort_values("Rank")
        if g.empty:
            continue

        ax.plot(
            g["Rank"],
            g["Cumulative % of Total"],
            linewidth=2.5,
            marker="o",
            markersize=3,
            label=str(date_label)
        )

    max_rank = int(chart_input["Rank"].max()) if not chart_input.empty else 1

    ax.set_title("Cumulative Contribution Curve")
    ax.set_xlabel("No. of Pax")
    ax.set_ylabel("% of Sewer Score")
    ax.set_xlim(1, max(max_rank, 2))
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax.grid(True, linestyle="-", alpha=0.3)
    ax.legend(title="Date")

    plt.tight_layout()
    return fig_to_png_bytes(fig)

# =========================================================
# BUILD CUMULATIVE DATA FOR SELECTED DATES
# =========================================================
cumulative_frames = []

for date_col in selected_dates:
    cum_df = prepare_cumulative_for_date(source_df, date_col, exclude_zero=exclude_zero)
    if not cum_df.empty:
        cumulative_frames.append(cum_df)

if not cumulative_frames:
    st.warning("No rows available after filtering.")
    st.stop()

combined_cum_df = pd.concat(cumulative_frames, ignore_index=True)

# Default/focus date for metrics/detail = latest selected date
focus_date = sorted(selected_dates, key=lambda x: pd.to_datetime(x, errors="coerce"))[-1]
focus_df = combined_cum_df[combined_cum_df["Date"] == focus_date].copy()

if focus_df.empty:
    st.warning("No data available for the latest selected date.")
    st.stop()

focus_total_score = int(focus_df["Total Score"].iloc[0])
focus_player_count = int(len(focus_df))
focus_top_score = int(focus_df["Score"].max())

# =========================================================
# HEADER METRICS
# =========================================================
st.subheader(f"Focus date: {focus_date}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Score", fmt_int(focus_total_score))
with col2:
    st.metric("Players Counted", fmt_int(focus_player_count))
with col3:
    st.metric("Top Player Score", fmt_int(focus_top_score))

# =========================================================
# QUERY RESULTS AS TABLE
# Runs across all selected dates
# =========================================================
st.subheader("Query Result")

query_rows = []

if query_mode == "%":
    for date_col in selected_dates:
        temp = combined_cum_df[combined_cum_df["Date"] == date_col].copy()
        result = get_pct_threshold_result(temp, query_value)
        if result is not None:
            query_rows.append(result)

    if query_rows:
        query_df = pd.DataFrame(query_rows)
        query_df["Cumulative Score"] = query_df["Cumulative Score"].map(lambda x: f"{int(x):,}")
        query_df["Actual Cumulative %"] = query_df["Actual Cumulative %"].map(lambda x: f"{x:.2f}%")
        query_df["Total Score"] = query_df["Total Score"].map(lambda x: f"{int(x):,}")

        st.dataframe(query_df, use_container_width=True)
    else:
        st.info("No threshold results found for the selected dates.")

else:
    for date_col in selected_dates:
        temp = combined_cum_df[combined_cum_df["Date"] == date_col].copy()
        result = get_pax_result(temp, query_value)
        if result is not None:
            query_rows.append(result)

    if query_rows:
        query_df = pd.DataFrame(query_rows)
        query_df["Cumulative Score"] = query_df["Cumulative Score"].map(lambda x: f"{int(x):,}")
        query_df["Cumulative % of Total"] = query_df["Cumulative % of Total"].map(lambda x: f"{x:.2f}%")
        query_df["Total Score"] = query_df["Total Score"].map(lambda x: f"{int(x):,}")

        st.dataframe(query_df, use_container_width=True)
    else:
        st.info("No pax results found for the selected dates.")

# =========================================================
# CHART
# =========================================================
st.subheader("Cumulative Score Plot")
chart_png = render_cumulative_chart(combined_cum_df[["Date", "Rank", "Cumulative % of Total"]].copy())
st.image(chart_png, use_container_width=False)

# =========================================================
# DETAIL TABLE FOR FOCUS DATE
# =========================================================
st.subheader(f"Cumulative Ranking Table — {focus_date}")

display_df = focus_df.copy()
display_df["Score"] = display_df["Score"].map(lambda x: f"{int(x):,}")
display_df["Cumulative Score"] = display_df["Cumulative Score"].map(lambda x: f"{int(x):,}")
display_df["Cumulative % of Total"] = display_df["Cumulative % of Total"].map(lambda x: f"{x:.2f}%")

st.dataframe(
    display_df[["Rank", "IGN", "Score", "Cumulative Score", "Cumulative % of Total"]],
    use_container_width=True
)
