import streamlit as st
import os
import pandas as pd

st.set_page_config(page_title="FilmFlation", layout="wide")

st.title("FilmFlation")
st.markdown(
    "Adjusting storyline dollar amounts for inflation to modernize plot stakes.   \n"
    "**It's a Wonderful Life** (1946)  \n"
    "Uncle Billy misplaces the bank deposit:  \n"
    "**$8,000 on Mon, Dec 24, 1945 (Christmas Eve)**"
)

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))


@st.cache_data
def load_data():
    raw = conn.query(
        "SELECT DECADE_YEAR, CPI_VALUE, CUMULATIVE_MULTIPLIER, "
        "DOLLAR_1945_WORTH_TODAY, AMOUNT_8000_ADJUSTED, DOLLAR_100_ADJUSTED, "
        "CUMULATIVE_INFLATION_PCT, DECADE_OVER_DECADE_PCT "
        "FROM FILMFLATION.PUBLIC.INFLATION_ADJUSTMENT ORDER BY DECADE_YEAR"
    )
    return raw


df = load_data()

# --- KPI row ---
latest = df.iloc[-1]
base = df.iloc[0]

with st.container(horizontal=True):
    st.metric(
        "Original Amount (Dec 1945)",
        f"${float(base['AMOUNT_8000_ADJUSTED']):,.0f}",
        border=True,
    )
    st.metric(
        "In Dec 2025 Dollars",
        f"${float(latest['AMOUNT_8000_ADJUSTED']):,.0f}",
        f"+{float(latest['CUMULATIVE_INFLATION_PCT']):.0f}% cumulative inflation",
        border=True,
    )
    st.metric(
        "1945 Dollar Multiplier",
        f"{float(latest['CUMULATIVE_MULTIPLIER']):.2f}x",
        f"$1 in 1945 = ${float(latest['DOLLAR_1945_WORTH_TODAY']):.2f} today",
        border=True,
    )

st.divider()

# --- $8,000 adjusted chart ---
with st.container(border=True):
    st.subheader("$8,000 Adjusted for Inflation")
    chart_df = pd.DataFrame({
        "Decade": [str(int(y)) for y in df["DECADE_YEAR"]],
        "Amount": [float(v) for v in df["AMOUNT_8000_ADJUSTED"]],
    }).set_index("Decade")
    st.area_chart(chart_df, y="Amount", x_label="Decade", y_label="Value (USD)", color="#4C78A8")

    # Value labels as metric chips
    cols = st.columns(len(df))
    for i, row in enumerate(df.itertuples()):
        with cols[i]:
            yr = str(int(row.DECADE_YEAR))
            amt = float(row.AMOUNT_8000_ADJUSTED)
            mult = float(row.CUMULATIVE_MULTIPLIER)
            st.caption(f"**{yr}**")
            st.caption(f"${amt:,.0f}")
            st.caption(f"{mult:.1f}x")

st.divider()

# --- Decade-over-decade bar chart ---
with st.container(border=True):
    st.subheader("Decade-over-Decade Inflation (%)")
    dod_rows = df[df["DECADE_OVER_DECADE_PCT"].notna()]
    dod_chart_df = pd.DataFrame({
        "Decade": [str(int(y)) for y in dod_rows["DECADE_YEAR"]],
        "Inflation %": [float(v) for v in dod_rows["DECADE_OVER_DECADE_PCT"]],
    }).set_index("Decade")
    st.bar_chart(dod_chart_df, y="Inflation %", x_label="Decade", y_label="Inflation (%)", color="#E45756")

    # Value labels
    cols = st.columns(len(dod_rows))
    for i, row in enumerate(dod_rows.itertuples()):
        with cols[i]:
            yr = str(int(row.DECADE_YEAR))
            pct = float(row.DECADE_OVER_DECADE_PCT)
            st.caption(f"**{yr}**")
            st.caption(f"+{pct:.1f}%")

st.divider()

# --- Data grid ---
with st.container(border=True):
    st.subheader("Full Inflation Data")
    st.dataframe(
        df,
        column_config={
            "DECADE_YEAR": st.column_config.NumberColumn("Decade", format="%d"),
            "CPI_VALUE": st.column_config.NumberColumn("CPI Index", format="%.1f"),
            "CUMULATIVE_MULTIPLIER": st.column_config.NumberColumn(
                "Multiplier", format="%.2fx"
            ),
            "DOLLAR_1945_WORTH_TODAY": st.column_config.NumberColumn(
                "$1 (1945) Worth", format="$%.2f"
            ),
            "AMOUNT_8000_ADJUSTED": st.column_config.NumberColumn(
                "$8,000 Adjusted", format="$%,.0f"
            ),
            "DOLLAR_100_ADJUSTED": st.column_config.NumberColumn(
                "$100 Adjusted", format="$%,.0f"
            ),
            "CUMULATIVE_INFLATION_PCT": st.column_config.NumberColumn(
                "Cumulative %", format="%.1f%%"
            ),
            "DECADE_OVER_DECADE_PCT": st.column_config.NumberColumn(
                "Decade Change %", format="%.1f%%"
            ),
        },
        hide_index=True,
    )

st.caption(
    "Source: U.S. Bureau of Labor Statistics CPI-U (All Items, Not Seasonally Adjusted) "
    "via Snowflake Marketplace. Built with CoCo."
)
