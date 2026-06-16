import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from io import BytesIO

st.title("Guild Ranks")

if "guilds_df" not in st.session_state or st.session_state.guilds_df is None:
    st.error("guilds_df not found in session state.")
    st.stop()

guilds_df = st.session_state.guilds_df.copy()

if guilds_df.empty:
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


def fig_to_png_bytes(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    png_bytes = buf.getvalue()
    plt.close(fig)
    return png_bytes

# =========================================================
# CACHED CHART RENDERERS
# These cache the actual rendered PNG bytes so the charts
# don't need to be rebuilt every time you switch pages.
# =========================================================
@st.cache_data(show_spinner=False)
def render_bump_chart(plot_df: pd.DataFrame) -> bytes:
    plot_df = plot_df.copy()

    selected_guilds = plot_df["guild"].dropna().unique().tolist()
    color_map = make_color_map(selected_guilds)

    date_values = sorted(plot_df["date"].dropna().unique())
    date_values = pd.to_datetime(date_values)

    if len(date_values) >= 2:
        span_days = max((date_values.max() - date_values.min()).days, 1)
        right_pad_days = max(2, int(span_days * 0.18))
    else:
        right_pad_days = 3

    right_label_x = date_values.max() + pd.Timedelta(days=right_pad_days)

    fig, ax = plt.subplots(figsize=(15, 8))
    fig.patch.set_facecolor("#eeeeee")
    ax.set_facecolor("#eeeeee")

    for guild in selected_guilds:
        g = plot_df[plot_df["guild"] == guild].sort_values("date")
        if g.empty:
            continue

        color = color_map[guild]

        ax.plot(
            g["date"],
            g["rank"],
            marker="o",
            linewidth=2.5,
            color=color
        )

        # Score labels at each point
        for _, row in g.iterrows():
            if pd.notna(row["score"]):
                ax.annotate(
                    fmt_score(row["score"]),
                    (row["date"], row["rank"]),
                    textcoords="offset points",
                    xytext=(6, 2),
                    ha="left",
                    fontsize=8,
                    color=color
                )

        # Guild label at final point
        last = g.iloc[-1]
        ax.text(
            right_label_x,
            last["rank"],
            str(guild),
            fontsize=11,
            color=color,
            ha="left",
            va="center",
            fontweight="bold"
        )

    ax.set_title("Guild Ranking Bump Chart")
    ax.set_xlabel("Date")
    ax.set_ylabel("Rank")

    max_rank = int(plot_df["rank"].max())
    ax.set_ylim(max_rank + 0.5, 0.5)
    ax.set_yticks(range(1, max_rank + 1))
    ax.grid(True, linestyle="--", alpha=0.3)

    ax.set_xticks(date_values)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

    ax.set_xlim(
        date_values.min() - pd.Timedelta(days=1),
        right_label_x + pd.Timedelta(days=2)
    )

    plt.tight_layout()
    return fig_to_png_bytes(fig)


@st.cache_data(show_spinner=False)
def render_score_chart(plot_df: pd.DataFrame) -> bytes:
    plot_df = plot_df.copy()

    selected_guilds = plot_df["guild"].dropna().unique().tolist()
    color_map = make_color_map(selected_guilds)

    score_df = plot_df.dropna(subset=["score"]).sort_values(["guild", "date"])
    date_values = sorted(score_df["date"].dropna().unique())
    date_values = pd.to_datetime(date_values)

    fig, ax = plt.subplots(figsize=(15, 8))
    fig.patch.set_facecolor("#eeeeee")
    ax.set_facecolor("#eeeeee")

    for guild in selected_guilds:
        g = score_df[score_df["guild"] == guild].sort_values("date")
        if g.empty:
            continue

        color = color_map[guild]

        ax.plot(
            g["date"],
            g["score"],
            marker="o",
            linewidth=2.5,
            color=color
        )

        last = g.iloc[-1]
        ax.text(
            last["date"] + pd.Timedelta(days=1),
            last["score"],
            f"{guild}",
            fontsize=11,
            color=color,
            ha="left",
            va="center",
            fontweight="bold"
        )

    ax.set_title("Guild Score Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score")
    ax.grid(True, linestyle="--", alpha=0.3)

    ax.yaxis.set_major_formatter(FuncFormatter(fmt_axis_commas))
    ax.set_xticks(date_values)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

    fig.autofmt_xdate()
    plt.tight_layout()
    return fig_to_png_bytes(fig)

# =========================================================
# SIDEBAR CONTROLS
# =========================================================
available_dates = sorted(plot_source["date"].dropna().dt.date.unique().tolist())
default_dates = available_dates

st.sidebar.header("Guild Rank Filters")
selected_dates = st.sidebar.multiselect(
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

selected_guilds = filtered["guild"].dropna().unique().tolist()

if not selected_guilds:
    st.warning("No guilds found for the selected dates.")
    st.stop()

plot_df = filtered[filtered["guild"].isin(selected_guilds)].copy()
plot_df = plot_df.sort_values(["guild", "date"])

# =========================================================
# 1) BUMP CHART
# =========================================================
st.subheader("Guild Ranking Bump Chart")
bump_chart_png = render_bump_chart(plot_df)
st.image(bump_chart_png, use_container_width=True)

# =========================================================
# 2) SCORE OVER TIME
# =========================================================
st.subheader("Guild Score Over Time")
score_chart_png = render_score_chart(plot_df)
st.image(score_chart_png, use_container_width=True)

# =========================================================
# RAW DATA
# =========================================================
st.subheader("Guild Rank Data")
st.dataframe(
    guilds_df.sort_values(["date", "rank"]),
    use_container_width=True
)
