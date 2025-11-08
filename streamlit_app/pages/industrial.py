import streamlit as st
import pandas as pd
import requests

# --------------------------------------------------
# CONFIG BASE
# --------------------------------------------------
st.set_page_config(page_title="Industrial", layout="wide")
st.title("Industrial")

BASE_URL = "http://api:8000"
SHOP_ID = 520400008
LIMIT = 50

# --------------------------------------------------
# STILE
# --------------------------------------------------
st.markdown(
    """
    <style>
    button[data-baseweb="tab"] {
        font-size: 1.05rem !important;
        padding: 0.6rem 1.3rem !important;
    }
    div[data-testid="metric-container"] {
        background: #f7f7f9;
        border: 1px solid #eee;
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# FETCH
# --------------------------------------------------
def fetch_data(endpoint: str, shop_id: int, limit: int = 50) -> pd.DataFrame:
    url = f"{BASE_URL}{endpoint}"
    params = {"shop_id": shop_id, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    first_key = next(iter(data))
    rows = data[first_key]
    return pd.DataFrame(rows)


tab_std, tab_more = st.tabs(["Lifting standard", "More tasks of industrial"])

# --------------------------------------------------
# TAB 1
# --------------------------------------------------
with tab_std:
    st.subheader("Lifting")
    try:
        df_l = fetch_data("/lifting", SHOP_ID, LIMIT)

        # selezione robot
        robot_list = sorted(df_l["sn"].unique())
        selected_robot = st.selectbox("Seleziona robot", robot_list)

        df_robot = df_l[df_l["sn"] == selected_robot]

        # KPI
        c1, c2, c3 = st.columns(3)
        c1.metric("Durata media (min)", round(df_robot["cur_duration"].mean(), 2))
        c2.metric("Distanza media (m)", round(df_robot["cur_mileage"].mean(), 2))
        c3.metric("Permanenza media (s)", round(df_robot["stay_duration"].mean(), 2))

        # task non completate (arrival_time NULL)
        st.subheader("Task non completate")
        incomplete = df_robot[df_robot["arrival_time"].isna()]
        if incomplete.empty:
            st.success("Nessuna task incompleta per questo robot.")
        else:
            st.dataframe(
                incomplete[
                    ["id", "begin_time", "destination", "robot_name", "sn", "shop_name"]
                ],
                use_container_width=True,
            )
            st.caption(f"Totale non completate: {len(incomplete)}")

        # grafici
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Durata media per destinazione – {selected_robot}")
            st.bar_chart(
                df_robot.groupby("destination")["cur_duration"].mean(),
                use_container_width=True,
            )
        with col2:
            st.caption(f"Andamento temporale – {selected_robot}")
            df_robot_time = df_robot.set_index("task_time")
            st.line_chart(df_robot_time[["cur_duration", "cur_mileage"]])

        # dati
        st.caption(f"Dati grezzi – {selected_robot}")
        st.dataframe(df_robot, use_container_width=True)

        # dettagli
        st.caption("Dettagli identificativi")
        info_cols = st.columns(4)
        info_cols[0].write(f"**SN**: {selected_robot}")
        info_cols[1].write(f"**Nome**: {df_robot['robot_name'].iloc[0] if not df_robot.empty else '-'}")
        info_cols[2].write(f"**MAC**: {df_robot['mac'].iloc[0] if not df_robot.empty else '-'}")
        info_cols[3].write(f"**Modello**: {df_robot['product_code'].iloc[0] if not df_robot.empty else '-'}")

    except Exception as e:
        st.error(f"Errore nel recupero lifting: {e}")

# --------------------------------------------------
# TAB 2
# --------------------------------------------------
with tab_more:
    st.subheader("More tasks of industrial")
    st.info("Qui puoi aggiungere altri endpoint quando li avrai.")
