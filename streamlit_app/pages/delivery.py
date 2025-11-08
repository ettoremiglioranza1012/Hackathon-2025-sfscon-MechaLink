import streamlit as st
import pandas as pd
import requests


def render():
    st.title("🤖 Delivery Task Dashboard")

    BASE_URL = "http://api:8000"
    SHOP_ID = 520400008
    LIMIT = 50


    def fetch_data(endpoint: str, shop_id: int, limit: int = 50) -> pd.DataFrame:
        url = f"{BASE_URL}{endpoint}"
        params = {"shop_id": shop_id, "limit": limit}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        first_key = next(iter(data))
        rows = data[first_key]
        return pd.DataFrame(rows)


    tab_greeter, tab_recovery, tab_call = st.tabs(["🟢 Greeter", "🟡 Recovery", "🔵 Call"])

    # ------------------------------------------------------------------
    # TAB GREETER
    # ------------------------------------------------------------------
    with tab_greeter:
        st.subheader("🟢 Greeter tasks")
        try:
            df_g = fetch_data("/delivery/greeter", SHOP_ID, LIMIT)

            # KPI
            c1, c2, c3 = st.columns(3)
            c1.metric("Durata media (min)", round(df_g["cur_duration"].mean(), 2))
            c2.metric("Distanza media (m)", round(df_g["cur_mileage"].mean(), 2))
            c3.metric("Permanenza media (s)", round(df_g["stay_duration"].mean(), 2))

            # task non completate
            st.subheader("Task non completate")
            g_incomplete = df_g[df_g["arrival_time"].isna()]
            if g_incomplete.empty:
                st.success("Nessuna task incompleta.")
            else:
                st.dataframe(
                    g_incomplete[
                        ["id", "begin_time", "destination", "robot_name", "sn", "shop_name"]
                    ],
                    use_container_width=True,
                )
                st.caption(f"Totale non completate: {len(g_incomplete)}")

            # Grafici
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.caption("Durata media per destinazione")
                st.bar_chart(
                    df_g.groupby("destination")["cur_duration"].mean(),
                    use_container_width=True
                )
            with col_g2:
                df_g_time = df_g.set_index("task_time")
                st.caption("Andamento durata e distanza")
                st.line_chart(df_g_time[["cur_duration", "cur_mileage"]])

            st.caption("Dati greeter")
            st.dataframe(df_g, use_container_width=True)

        except Exception as e:
            st.error(f"Errore nel recupero greeter: {e}")

    # ------------------------------------------------------------------
    # TAB RECOVERY
    # ------------------------------------------------------------------
    with tab_recovery:
        st.subheader("🟡 Recovery tasks")
        try:
            df_r = fetch_data("/delivery/recovery", SHOP_ID, LIMIT)

            # KPI (nomi reali: duration, mileage)
            c1, c2, c3 = st.columns(3)
            c1.metric("Durata media (min)", round(df_r["duration"].mean(), 2))
            c2.metric("Distanza media (m)", round(df_r["mileage"].mean(), 2))
            # qui non hai stay_duration, quindi metti un fallback
            c3.metric("Task totali", len(df_r))

            # task non completate (se la tabella ha arrival_time; se non c’è, salta)
            if "arrival_time" in df_r.columns:
                st.subheader("Task non completate")
                r_incomplete = df_r[df_r["arrival_time"].isna()]
                if r_incomplete.empty:
                    st.success("Nessuna task incompleta.")
                else:
                    st.dataframe(
                        r_incomplete[
                            ["id", "task_time", "robot_name", "sn", "shop_name"]
                        ],
                        use_container_width=True,
                    )
                    st.caption(f"Totale non completate: {len(r_incomplete)}")

            st.caption("Distanza media per shop")
            st.bar_chart(
                df_r.groupby("shop_name")["mileage"].mean(),
                use_container_width=True
            )

            st.caption("Dati recovery")
            st.dataframe(df_r, use_container_width=True)

        except Exception as e:
            st.error(f"Errore nel recupero recovery: {e}")

    # ------------------------------------------------------------------
    # TAB CALL
    # ------------------------------------------------------------------
    with tab_call:
        st.subheader("🔵 Call tasks")
        try:
            df_c = fetch_data("/delivery/call", SHOP_ID, LIMIT)

            # KPI
            c1, c2, c3 = st.columns(3)
            c1.metric("Durata media (min)", round(df_c["cur_duration"].mean(), 2))
            c2.metric("Distanza media (m)", round(df_c["cur_mileage"].mean(), 2) if "cur_mileage" in df_c.columns else 0)
            c3.metric("Permanenza media (s)", round(df_c["stay_duration"].mean(), 2))

            # task non completate
            if "arrival_time" in df_c.columns:
                st.subheader("Task non completate")
                c_incomplete = df_c[df_c["arrival_time"].isna()]
                if c_incomplete.empty:
                    st.success("Nessuna task incompleta.")
                else:
                    st.dataframe(
                        c_incomplete[
                            ["id", "begin_time", "destination", "robot_name", "sn", "shop_name"]
                        ],
                        use_container_width=True,
                    )
                    st.caption(f"Totale non completate: {len(c_incomplete)}")

            st.caption("Permanenza media per destinazione")
            st.bar_chart(
                df_c.groupby("destination")["stay_duration"].mean(),
                use_container_width=True
            )

            st.caption("Dati call")
            st.dataframe(df_c, use_container_width=True)

        except Exception as e:
            st.error(f"Errore nel recupero call: {e}")
