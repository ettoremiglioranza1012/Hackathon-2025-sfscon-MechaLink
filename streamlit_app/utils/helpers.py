import streamlit as st
import pandas as pd
import matplotlib

import matplotlib.pyplot as plt
import requests as req

matplotlib.use("TkAgg")  # or "Qt5Agg", depending on your system


def show_info_box(title, message):
    st.info(f"**{title}**: {message}")


def retrieve_and_plot_shop_analysis(
    start_time: str = 0,
    end_time: str = 0,
    shop_id: str = 0,
    time_unit: str = 0,
    timezone_offset: str = 0,
):
    res = req.get(
        "https://sfscon.tmkhosting.net/analysis/shops/general?start_time=1761300000&end_time=1762470001&shop_id=541100015&time_unit=day&timezone_offset=0",
        headers={"x-key": "H4ckath0n2025!Telmek0m"},
    )
    if res.status_code != 200:
        print("status code: ", res.status_code)
        return None

    encoded_json = res.json()
    # return encoded_json
    df = pd.DataFrame(encoded_json["data"]["chart"])
    # Create figure and plot
    fig, ax = plt.subplots()
    fig = df.plot(x="task_time", y=["lively_count", "silent_count", "new_count"], ax=ax)
    ax.set_title("Shop Analysis Chart")
    ax.set_xlabel("Date")
    ax.set_ylabel("Count")

    # Display in Streamlit
    # st.pyplot(fig)
    plt.show()


if __name__ == "__main__":
    print(retrieve_and_plot_shop_analysis())
