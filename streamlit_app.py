import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

# Set the title and favicon that appear in the browser tab
st.set_page_config(
    page_title="Insurgence",
    page_icon=":skull_and_crossbones:",
    layout="wide",
)

# =========================================================
# LOADERS
# =========================================================
@st.cache_data
def load_guild_ranks():
    rows = st.secrets["tables"]["guild_ranks"]["rows"]

    guilds_df = pd.DataFrame(rows)

    # Ensure expected columns exist even if some rows are incomplete
    expected_cols = ["week", "date", "rank", "guild", "score"]
    for col in expected_cols:
        if col not in guilds_df.columns:
            guilds_df[col] = pd.NA

    # Clean dtypes
    guilds_df["week"] = pd.to_numeric(guilds_df["week"], errors="coerce").astype("Int64")
    guilds_df["rank"] = pd.to_numeric(guilds_df["rank"], errors="coerce").astype("Int64")
    guilds_df["score"] = pd.to_numeric(guilds_df["score"], errors="coerce")
    guilds_df["date"] = pd.to_datetime(guilds_df["date"], errors="coerce")
    guilds_df["guild"] = guilds_df["guild"].astype("string")

    # Sort
    guilds_df = guilds_df.sort_values(
        by=["date", "rank"],
        ascending=[True, True],
        na_position="last"
    ).reset_index(drop=True)

    return guilds_df


@st.cache_data
def load_sewers_score():
    raw = st.secrets["tables"]["sewers_score"]

    df = pd.DataFrame.from_dict(raw, orient="index")
    df.index.name = "IGN"
    df = df.reset_index()

    # Convert all non-IGN columns to numeric
    value_cols = [c for c in df.columns if c != "IGN"]
    for col in value_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort date columns chronologically
    sorted_value_cols = sorted(
        value_cols,
        key=lambda x: pd.to_datetime(x, errors="coerce")
    )
    df = df[["IGN"] + sorted_value_cols]

    return df


# =========================================================
# LOAD DATA
# =========================================================
guilds_df = load_guild_ranks()
df = load_sewers_score()

st.session_state.guilds_df = guilds_df
st.session_state.df = df
st.session_state.names = sorted(df["IGN"].dropna().unique().tolist())

# =========================================================
# PAGE TITLE
# =========================================================
st.title("Guild Ranks")

if guilds_df is None or guilds_df.empty:
    st.warning("guilds_df is empty.")
    st.stop()

# =========================================================
# CLEAN / PREP
# =========================================================
plot_source = guilds_df.copy()

plot_source["date"] = pd.to_datetime(plot_source["date"], errors="coerce")
plot_source["week"] = pd.to_numeric(plot_source["week"], errors="coerce")
plot_source["rank"] = pd.to_numeric(plot_source["rank"], errors="coerce")
plot_source["score"] = pd.to_numeric(plot_source["score"], errors="coerce")
plot_source["guild"] = plot_source["guild"].astype("string")

plot_source = plot_source.dropna(subset=["date", "rank"])
plot_source = plot_source.sort_values(["date", "rank"]).reset_index(drop=True)

# =========================================================
# HELPERS
# =========================================================
def fmt_score(x):
    if pd.isna(x):
        return ""
    return f"{int(x):,}"

def fmt_axis_commas(x, pos):
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)

def make_color_map(items):
    cmap = plt.get_cmap("tab20")
    return {item: cmap(i % 20) for i, item in enumerate(items)}

# =========================================================
# CONTROLS
# =========================================================
available_dates = sorted(plot_source["date"].dropna().dt.date.unique().tolist())
default_dates = available_dates

selected_dates = st.multiselect(
    "Select dates",
    options=available_dates,
    default=default_dates
)

if not selected_dates:
    st.warning("Please select at least one date.")
    st.stop()

selected_dates_ts = pd.to_datetime(selected_dates)

filtered = plot_source[plot_source["date"].isin(selected_dates_ts)].copy()

if filtered.empty:
    st.warning("No data available for the selected dates.")
    st.stop()

# Use all guilds within selected dates
selected_guilds = filtered["guild"].dropna().unique().tolist()

if not selected_guilds:
    st.warning("No guilds found for the selected dates.")
    st.stop()

plot_df = filtered[filtered["guild"].isin(selected_guilds)].copy()
plot_df = plot_df.sort_values(["guild", "date"])

color_map = make_color_map(selected_guilds)

date_values = sorted(plot_df["date"].dropna().unique())
date_values = pd.to_datetime(date_values)

if len(date_values) >= 2:
    span_days = max((date_values.max() - date_values.min()).days, 1)
    right_pad_days = max(2, int(span_days * 0.18))
else:
    right_pad_days = 3

right_label_x = date_values.max() + pd.Timedelta(days=right_pad_days)

# =========================================================
# 1) BUMP CHART
# =========================================================
st.subheader("Guild Ranking Bump Chart")

fig1, ax1 = plt.subplots(figsize=(15, 8))
fig1.patch.set_facecolor("#eeeeee")
ax1.set_facecolor("#eeeeee")

for guild in selected_guilds:
    g = plot_df[plot_df["guild"] == guild].sort_values("date")
    if g.empty:
        continue

    color = color_map[guild]

    ax1.plot(
        g["date"],
        g["rank"],
        marker="o",
        linewidth=2.5,
        color=color
    )

    # Score labels at every plotted point
    for _, row in g.iterrows():
        if pd.notna(row["score"]):
            ax1.annotate(
                fmt_score(row["score"]),
                (row["date"], row["rank"]),
                textcoords="offset points",
                xytext=(6, 2),
                ha="left",
                fontsize=8,
                color=color
            )

    # Guild name on the right side at the last available point
    last = g.iloc[-1]
    ax1.text(
        right_label_x,
        last["rank"],
        str(guild),
        fontsize=11,
        color=color,
        ha="left",
        va="center",
        fontweight="bold"
    )

ax1.set_title("Guild Ranking Bump Chart")
ax1.set_xlabel("Date")
ax1.set_ylabel("Rank")

# Invert rank axis so 1 is at the top
max_rank = int(plot_df["rank"].max())
ax1.set_ylim(max_rank + 0.5, 0.5)

ax1.set_yticks(range(1, max_rank + 1))
ax1.grid(True, linestyle="--", alpha=0.3)

# X-axis formatting
ax1.set_xticks(date_values)
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

# Add right padding so guild labels fit
ax1.set_xlim(
    date_values.min() - pd.Timedelta(days=1),
    right_label_x + pd.Timedelta(days=2)
)

plt.tight_layout()
st.pyplot(fig1, use_container_width=True)

# =========================================================
# 2) SCORE OVER TIME
# =========================================================
st.subheader("Guild Score Over Time")

score_df = plot_df.copy()
score_df = score_df.dropna(subset=["score"])
score_df = score_df.sort_values(["guild", "date"])

fig2, ax2 = plt.subplots(figsize=(15, 8))
fig2.patch.set_facecolor("#eeeeee")
ax2.set_facecolor("#eeeeee")

for guild in selected_guilds:
    g = score_df[score_df["guild"] == guild].sort_values("date")
    if g.empty:
        continue

    color = color_map[guild]

    ax2.plot(
        g["date"],
        g["score"],
        marker="o",
        linewidth=2.5,
        color=color
    )

    last = g.iloc[-1]
    ax2.text(
        last["date"] + pd.Timedelta(days=1),
        last["score"],
        f"{guild}",
        fontsize=11,
        color=color,
        ha="left",
        va="center",
        fontweight="bold"
    )

ax2.set_title("Guild Score Over Time")
ax2.set_xlabel("Date")
ax2.set_ylabel("Score")
ax2.grid(True, linestyle="--", alpha=0.3)

ax2.yaxis.set_major_formatter(FuncFormatter(fmt_axis_commas))
ax2.set_xticks(date_values)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

fig2.autofmt_xdate()
plt.tight_layout()
st.pyplot(fig2, use_container_width=True)

# =========================================================
# RAW DATAFRAME
# =========================================================
st.subheader("Guild Rank Data")
st.dataframe(
    guilds_df.sort_values(["date", "rank"]),
    use_container_width=True
)