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

UDTF = "FILMFLATION.PUBLIC.CALC_INFLATION"


def load_inflation(base_year, base_month, step_years):
    session = conn.session()
    return session.sql(
        f"SELECT * FROM TABLE({UDTF}({base_year}, {base_month}, {step_years}))"
    ).to_pandas()


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

    step_years = st.select_slider(
        "Year Interval [1, 2, 5 or 10]",
        options=[1, 2, 5, 10],
        value=film["step_years"],
    )

scene = next(s for s in film["scenes"] if s["label"] == scene_label)

base_year = scene.get("base_year_override", film["base_year"])
base_month = film["base_month"]
base_month_label = film["base_month_label"]
original_amount = scene["original_amount"]
amount_label = f"${original_amount:,}"
chart_color = scene["chart_color"]

df = load_inflation(base_year, base_month, step_years)

# Compute amount columns in Python
df["AMOUNT_ADJUSTED"] = (original_amount * df["CUMULATIVE_MULTIPLIER"]).round(2)
df["DOLLAR_WORTH_TODAY"] = df["CUMULATIVE_MULTIPLIER"].round(2)

# --- Title ---
st.title("FilmFlation")
st.caption("If you've ever watched a movie that takes place in the past and wondered:  \n\"How much is that worth in today's dollars?\"  \n...then this app is for you.")
st.markdown(f"**{film_name}** ({film['year']})  \n{scene['description']}")

# --- KPI row ---
latest = df.iloc[-1]
latest_year = int(latest["PERIOD_YEAR"])

with st.container(horizontal=True):
    st.metric(
        f"Original Amount ({base_month_label} {base_year})",
        f"${original_amount:,.0f}",
        border=True,
    )
    st.metric(
        f"In {base_month_label} {latest_year} Dollars",
        f"${float(latest['AMOUNT_ADJUSTED']):,.0f}",
        f"+{float(latest['CUMULATIVE_INFLATION_PCT']):.0f}% cumulative inflation",
        border=True,
    )
    st.metric(
        f"{base_year} Dollar Multiplier",
        f"{float(latest['CUMULATIVE_MULTIPLIER']):.2f}x",
        f"$1 in {base_year} = ${float(latest['DOLLAR_WORTH_TODAY']):.2f} today",
        border=True,
    )

st.divider()

# --- Amount adjusted chart ---
with st.container(border=True):
    st.subheader(f"{amount_label} Adjusted for Inflation")

    chart_df = pd.DataFrame({
        "Year": [str(int(y)) for y in df["PERIOD_YEAR"]],
        "Amount": [float(v) for v in df["AMOUNT_ADJUSTED"]],
        "Multiplier": [float(v) for v in df["CUMULATIVE_MULTIPLIER"]],
        "Cumulative": [float(v) for v in df["CUMULATIVE_INFLATION_PCT"]],
        "PoPPct": [float(v) if v is not None else 0.0 for v in df["PERIOD_OVER_PERIOD_PCT"]],
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
            x=alt.X("Year:N", sort=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Amount:Q", title="Value (USD)", axis=alt.Axis(format="$,.0f")),
            tooltip=[
                alt.Tooltip("Year:N", title="Year"),
                alt.Tooltip("Amount:Q", title=f"{amount_label} Adjusted", format="$,.0f"),
                alt.Tooltip("Multiplier:Q", title="Multiplier", format=".2f"),
                alt.Tooltip("Cumulative:Q", title="Cumulative Inflation %", format=",.1f"),
                alt.Tooltip("PoPPct:Q", title="Period Change %", format=",.1f"),
            ],
        )
        .properties(height=350)
    )

    points = (
        alt.Chart(chart_df)
        .mark_point(filled=True, size=60, color="white", stroke=chart_color, strokeWidth=2)
        .encode(
            x=alt.X("Year:N", sort=None),
            y=alt.Y("Amount:Q", axis=alt.Axis(format="$,.0f")),
        )
    )

    labels = (
        alt.Chart(chart_df)
        .mark_text(dy=-15, fontSize=11, fontWeight="bold", color="white")
        .encode(
            x=alt.X("Year:N", sort=None),
            y=alt.Y("Amount:Q", axis=alt.Axis(format="$,.0f")),
            text=alt.Text("Amount:Q", format="$,.0f"),
        )
    )

    st.altair_chart(area + points + labels)

st.divider()

# --- Period-over-period bar chart ---
with st.container(border=True):
    period_label = "Decade" if step_years == 10 else f"{step_years}-Year"
    st.subheader(f"{period_label}-over-{period_label} Inflation (%)")

    pop_rows = df[df["PERIOD_OVER_PERIOD_PCT"].notna()]
    pop_df = pd.DataFrame({
        "Year": [str(int(y)) for y in pop_rows["PERIOD_YEAR"]],
        "Pct": [float(v) for v in pop_rows["PERIOD_OVER_PERIOD_PCT"]],
        "Amount": [float(v) for v in pop_rows["AMOUNT_ADJUSTED"]],
        "Cumulative": [float(v) for v in pop_rows["CUMULATIVE_INFLATION_PCT"]],
    })

    bars = (
        alt.Chart(pop_df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Year:N", sort=None, axis=alt.Axis(labelAngle=0)),
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
                alt.Tooltip("Year:N", title="Year"),
                alt.Tooltip("Pct:Q", title=f"{period_label} Change %", format=",.1f"),
                alt.Tooltip("Cumulative:Q", title="Cumulative Inflation %", format=",.1f"),
                alt.Tooltip("Amount:Q", title=f"{amount_label} Adjusted", format="$,.0f"),
            ],
        )
        .properties(height=300)
    )

    bar_labels = (
        alt.Chart(pop_df)
        .mark_text(dy=-10, fontSize=11, fontWeight="bold")
        .encode(
            x=alt.X("Year:N", sort=None),
            y=alt.Y("Pct:Q"),
            text=alt.Text("Pct:Q", format=".1f"),
        )
    )

    st.altair_chart(bars + bar_labels)

st.divider()

# --- Data grid ---
with st.container(border=True):
    st.subheader("Full Inflation Data")

    display_df = df[["PERIOD_YEAR", "CPI_VALUE", "CUMULATIVE_MULTIPLIER",
                     "DOLLAR_WORTH_TODAY", "AMOUNT_ADJUSTED",
                     "CUMULATIVE_INFLATION_PCT", "PERIOD_OVER_PERIOD_PCT"]].copy()

    st.dataframe(
        display_df,
        column_config={
            "PERIOD_YEAR": st.column_config.NumberColumn("Year", format="%d"),
            "CPI_VALUE": st.column_config.NumberColumn("CPI Index", format="%.1f"),
            "CUMULATIVE_MULTIPLIER": st.column_config.NumberColumn("Multiplier", format="%.2fx"),
            "DOLLAR_WORTH_TODAY": st.column_config.NumberColumn(f"$1 ({base_year}) Worth", format="$%.2f"),
            "AMOUNT_ADJUSTED": st.column_config.NumberColumn(f"{amount_label} Adjusted", format="$%,.0f"),
            "CUMULATIVE_INFLATION_PCT": st.column_config.NumberColumn("Cumulative %", format="%.1f%%"),
            "PERIOD_OVER_PERIOD_PCT": st.column_config.NumberColumn(f"{period_label} Change %", format="%.1f%%"),
        },
        hide_index=True,
    )

st.caption(
    "Source: U.S. Bureau of Labor Statistics CPI-U (All Items, Not Seasonally Adjusted) "
    "via Snowflake Marketplace. Built with CoCo."
)
