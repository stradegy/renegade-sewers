import streamlit as st
import pandas as pd

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title="Insurgence",
    page_icon=":skull_and_crossbones:",
    layout="wide",
)

# =========================================================
# SHARED LOADERS
# =========================================================
@st.cache_data
def load_guild_ranks():
    rows = st.secrets["tables"]["guild_ranks"]["rows"]

    guilds_df = pd.DataFrame(rows)

    expected_cols = ["week", "date", "rank", "guild", "score"]
    for col in expected_cols:
        if col not in guilds_df.columns:
            guilds_df[col] = pd.NA

    guilds_df["week"] = pd.to_numeric(guilds_df["week"], errors="coerce").astype("Int64")
    guilds_df["rank"] = pd.to_numeric(guilds_df["rank"], errors="coerce").astype("Int64")
    guilds_df["score"] = pd.to_numeric(guilds_df["score"], errors="coerce").astype("Int64")
    guilds_df["date"] = pd.to_datetime(guilds_df["date"], errors="coerce")
    guilds_df["guild"] = guilds_df["guild"].astype("string")

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

    value_cols = [c for c in df.columns if c != "IGN"]
    for col in value_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    sorted_value_cols = sorted(
        value_cols,
        key=lambda x: pd.to_datetime(x, errors="coerce")
    )
    df = df[["IGN"] + sorted_value_cols]

    return df


# =========================================================
# BOOTSTRAP SHARED STATE
# Widgets in the entrypoint can persist across page switches,
# and this file acts as the common frame/router for all pages.
# [1](https://github.com/streamlit/docs/blob/main/content/develop/concepts/architecture/caching.md)[2](https://discuss.streamlit.io/t/automatic-data-update/42385)
# =========================================================
guilds_df = load_guild_ranks()
df = load_sewers_score()

st.session_state.guilds_df = guilds_df
st.session_state.df = df
st.session_state.names = sorted(df["IGN"].dropna().unique().tolist())

# Optional shared helpers for sewers_score page later
st.session_state.dates = [c for c in df.columns if c != "IGN"]

# =========================================================
# NAVIGATION
# Using top navigation keeps the sidebar free for page filters.
# st.navigation supports "sidebar", "top", or "hidden".
# [1](https://github.com/streamlit/docs/blob/main/content/develop/concepts/architecture/caching.md)
# =========================================================
pg = st.navigation(
    [
        st.Page("app_pages/guild_ranks.py", title="Guild Ranks", icon=":material/groups:"),
        st.Page("app_pages/sewers_score.py", title="Sewers Score", icon=":material/insights:")
    ],
    position="top",
    expanded=True,
)

pg.run()