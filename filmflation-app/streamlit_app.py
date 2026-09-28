import streamlit as st
import altair as alt
import os
import json
import pandas as pd

st.set_page_config(page_title="FilmFlation", layout="wide")

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "films_config.json")
with open(CONFIG_PATH) as f:
    FILMS = json.load(f)

FILM_INDEX = {film["film"]: film for film in FILMS}


def load_table(table_fqn):
    session = conn.session()
    return session.sql(f"SELECT * FROM {table_fqn} ORDER BY DECADE_YEAR").to_pandas()


# --- Sidebar ---
with st.sidebar:
    st.header("Select a Film")
    film_name = st.selectbox(
        "Film",
        [f["film"] for f in FILMS],
        label_visibility="collapsed",
    )
    film = FILM_INDEX[film_name]
    scene_labels = [s["label"] for s in film["scenes"]]
    scene_label = st.selectbox("Which scene?", scene_labels)

scene = next(s for s in film["scenes"] if s["label"] == scene_label)

# Resolve per-scene overrides (e.g. Bank Run uses a different table/base year)
table_fqn = scene.get("table_override", film["table"])
dollar_col = scene.get("dollar_col_override", film["dollar_col"])
base_year = scene.get("base_year_override", film["base_year"])
base_month = film["base_month"]
amount_col = scene["amount_col"]
original_amount = scene["original_amount"]
amount_label = f"${original_amount:,}"
chart_color = scene["chart_color"]

df = load_table(table_fqn)

# --- Title ---
st.title("FilmFlation")
st.caption("\"How much is that worth in today's dollars?\"")
st.markdown(f"**{film_name}** ({film['year']})  \n{scene['description']}")

# --- KPI row ---
latest = df.iloc[-1]
latest_year = int(latest["DECADE_YEAR"])

with st.container(horizontal=True):
    st.metric(
        f"Original Amount ({base_month} {base_year})",
        f"${original_amount:,.0f}",
        border=True,
    )
    st.metric(
        f"In {base_month} {latest_year} Dollars",
        f"${float(latest[amount_col]):,.0f}",
        f"+{float(latest['CUMULATIVE_INFLATION_PCT']):.0f}% cumulative inflation",
        border=True,
    )
    st.metric(
        f"{base_year} Dollar Multiplier",
        f"{float(latest['CUMULATIVE_MULTIPLIER']):.2f}x",
        f"$1 in {base_year} = ${float(latest[dollar_col]):.2f} today",
        border=True,
    )

st.divider()

# --- Amount adjusted chart ---
with st.container(border=True):
    st.subheader(f"{amount_label} Adjusted for Inflation")

    chart_df = pd.DataFrame({
        "Decade": [str(int(y)) for y in df["DECADE_YEAR"]],
        "Amount": [float(v) for v in df[amount_col]],
        "Multiplier": [float(v) for v in df["CUMULATIVE_MULTIPLIER"]],
        "Cumulative": [float(v) for v in df["CUMULATIVE_INFLATION_PCT"]],
        "DodPct": [float(v) if v is not None else 0.0 for v in df["DECADE_OVER_DECADE_PCT"]],
    })

    r, g, b = (int(chart_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    area = (
        alt.Chart(chart_df)
        .mark_area(
            line={"color": chart_color},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color=chart_color, offset=1),
                    alt.GradientStop(color=f"rgba({r},{g},{b},0.1)", offset=0),
                ],
                x1=1, x2=1, y1=1, y2=0,
            ),
        )
        .encode(
            x=alt.X("Decade:N", sort=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Amount:Q", title="Value (USD)"),
            tooltip=[
                alt.Tooltip("Decade:N", title="Year"),
                alt.Tooltip("Amount:Q", title=f"{amount_label} Adjusted", format="$,.0f"),
                alt.Tooltip("Multiplier:Q", title="Multiplier", format=".2f"),
                alt.Tooltip("Cumulative:Q", title="Cumulative Inflation %", format=",.1f"),
                alt.Tooltip("DodPct:Q", title="Decade Change %", format=",.1f"),
            ],
        )
        .properties(height=350)
    )

    points = (
        alt.Chart(chart_df)
        .mark_point(filled=True, size=60, color="white", stroke=chart_color, strokeWidth=2)
        .encode(
            x=alt.X("Decade:N", sort=None),
            y=alt.Y("Amount:Q"),
        )
    )

    labels = (
        alt.Chart(chart_df)
        .mark_text(dy=-15, fontSize=11, fontWeight="bold", color="white")
        .encode(
            x=alt.X("Decade:N", sort=None),
            y=alt.Y("Amount:Q"),
            text=alt.Text("Amount:Q", format="$,.0f"),
        )
    )

    st.altair_chart(area + points + labels)

st.divider()

# --- Decade-over-decade bar chart ---
with st.container(border=True):
    st.subheader("Decade-over-Decade Inflation (%)")

    dod_rows = df[df["DECADE_OVER_DECADE_PCT"].notna()]
    dod_df = pd.DataFrame({
        "Decade": [str(int(y)) for y in dod_rows["DECADE_YEAR"]],
        "Pct": [float(v) for v in dod_rows["DECADE_OVER_DECADE_PCT"]],
        "Amount": [float(v) for v in dod_rows[amount_col]],
        "Cumulative": [float(v) for v in dod_rows["CUMULATIVE_INFLATION_PCT"]],
    })

    bars = (
        alt.Chart(dod_df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Decade:N", sort=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Pct:Q", title="Inflation (%)"),
            color=alt.Color(
                "Pct:Q",
                scale=alt.Scale(
                    domain=[18, 30, 45, 70, 97],
                    range=["#4C78A8", "#54B399", "#EECA3B", "#E58606", "#E45756"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Decade:N", title="Decade"),
                alt.Tooltip("Pct:Q", title="Decade Change %", format=",.1f"),
                alt.Tooltip("Cumulative:Q", title="Cumulative Inflation %", format=",.1f"),
                alt.Tooltip("Amount:Q", title=f"{amount_label} Adjusted", format="$,.0f"),
            ],
        )
        .properties(height=300)
    )

    bar_labels = (
        alt.Chart(dod_df)
        .mark_text(dy=-10, fontSize=11, fontWeight="bold")
        .encode(
            x=alt.X("Decade:N", sort=None),
            y=alt.Y("Pct:Q"),
            text=alt.Text("Pct:Q", format=".1f"),
        )
    )

    st.altair_chart(bars + bar_labels)

st.divider()

# --- Data grid ---
with st.container(border=True):
    st.subheader("Full Inflation Data")

    col_config = {
        "DECADE_YEAR": st.column_config.NumberColumn("Decade", format="%d"),
        "CPI_VALUE": st.column_config.NumberColumn("CPI Index", format="%.1f"),
        "CUMULATIVE_MULTIPLIER": st.column_config.NumberColumn("Multiplier", format="%.2fx"),
        dollar_col: st.column_config.NumberColumn(f"$1 ({base_year}) Worth", format="$%.2f"),
        amount_col: st.column_config.NumberColumn(f"{amount_label} Adjusted", format="$%,.0f"),
        "CUMULATIVE_INFLATION_PCT": st.column_config.NumberColumn("Cumulative %", format="%.1f%%"),
        "DECADE_OVER_DECADE_PCT": st.column_config.NumberColumn("Decade Change %", format="%.1f%%"),
    }

    display_cols = [c for c in col_config if c in df.columns]
    st.dataframe(df[display_cols], column_config=col_config, hide_index=True)

st.caption(
    "Source: U.S. Bureau of Labor Statistics CPI-U (All Items, Not Seasonally Adjusted) "
    "via Snowflake Marketplace. Built with CoCo."
)
