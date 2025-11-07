import streamlit as st
from datetime import datetime
import pandas as pd
import matplotlib
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import requests as req
import os
import plotly.express as px
from typing import Literal

# TODO: remove for dashboard app usage
# matplotlib.use("TkAgg")

load_dotenv()
try:
    API_KEY = os.getenv("API_KEY")
except Exception:
    raise Exception("Unable to retrieve API KEY")

BASE_ADDRESS = "https://sfscon.tmkhosting.net"

# IMPORTANT: all these endpoints only require three inputs:
# 1. start_time: unix timestamp (reported as int seconds)
# 2. end_time: unix timestamp (reported as int seconds)
# 3. shop_id: integer

ENDPOINTS_FIXED_INPUT = {
    "analysis": [
        "shops/general",
        "shops/cleaning/detail",
        "shops/cleaning",
        "shops/industrial",
        "shops/delivery",
        "shops/cruise",
        "shops/lead",
        "shops/solicit",
        "shops/recovery",
        "shops/call",
        "robot/general",
    ],
    "statistics": ["shops/general", "robots/general", "robots/operations"],
}


class ApiUriConstructor:
    """
    A utility class used to create lists of valid endpoints.
    NOTE: it is left to the programmer to check whether the desired endpoint
    accepts time_unit as a query parameter.
    """

    def __init__(
        self,
        base_address: str,
        endpoint_type: Literal["analysis", "statistics"],
        start_time: int,
        end_time: int,
        shop_id: int,
        time_unit: Literal["day", "hour"] | None = None,
    ):
        self.base_address = base_address
        self.endpoint_type = endpoint_type
        self.start_time = start_time
        self.end_time = end_time
        self.shop_id = shop_id
        self.time_unit = time_unit

    def build_uri(self, endpoint: str):
        """
        This method returns the full URI to which submit a request.
        If a time_unit parameter has been filled when an instance of the class
        was created, then it will be added to the URI.

        NOTE: This approach is error prone and it will need some adjustments in the future.
        """
        if self.time_unit:
            uri = f"{self.base_address}/{self.endpoint_type}/{endpoint}?start_time={self.start_time}&end_time={self.end_time}&shop_id={self.shop_id}"
        else:
            uri = f"{self.base_address}/{self.endpoint_type}/{endpoint}?start_time={self.start_time}&end_time={self.end_time}&shop_id={self.shop_id}"

        return uri

    def build_uri_list(self):
        """
        Build a list of valid endpoints starting from the type.
        """
        res = []
        try:
            for endpoint in ENDPOINTS_FIXED_INPUT[self.endpoint_type]:
                res.append(
                    f"{self.base_address}/{self.endpoint_type}/{endpoint}?start_time={self.start_time}&end_time={self.end_time}&shop_id={self.shop_id}"
                )
        except Exception as e:
            raise ValueError(f"Error: {e}")
        return res


class ApiRetriever:
    """
    Use this class to retrieve information from the API endpoint
    Args:
        resource_uri (str): the URI to the endpoint
        api_key (str): the api_key to use
    Returns:
        A JSON-like object for further analysis
    """

    def __init__(self, resource_uri: str, api_key: str | None = None):
        self.resource_uri = resource_uri
        self.api_key = api_key

    def get_request(self):
        """
        Performs a GET request to the indicated resource_uri checking if it succeded.
        If the call succedes, it returns the data retrieved as a JSON.
        """
        if self.api_key:
            res = req.get(self.resource_uri, headers={"x-key": self.api_key})
        else:
            res = req.get(self.resource_uri)

        if res.status_code == 200:
            return res.json()
        else:
            raise Exception(
                f"Call to {self.resource_uri} failed with code {res.status_code}"
            )


def show_info_box(title, message):
    st.info(f"**{title}**: {message}")


def dt_to_sec(dt: datetime) -> int:
    """
    convert datetime to UNIX seconds
    """
    return int(dt.timestamp())


def retrieve_and_plot_shop_analysis(
    start_time: datetime,
    end_time: datetime,
    shop_id: int = 0,
    time_unit: Literal["day", "hour"] = "day",
    timezone_offset: int = 0,
):
    start_time_converted = dt_to_sec(start_time)
    end_time_converted = dt_to_sec(end_time)

    constructor = ApiUriConstructor(
        BASE_ADDRESS,
        "analysis",
        start_time_converted,
        end_time_converted,
        541100015,
        "hour",
    )

    uri = constructor.build_uri("shops/general")
    retriever = ApiRetriever(
        # f"https://sfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["data"]["chart"])

    # Create figure and plot
    fig = px.line(
        df,
        x="task_time",
        y=["lively_count", "silent_count", "new_count"],
        title="Shop Activity Over Time",
        labels={"task_time": "Date", "value": "Count", "variable": "Type"},
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    print(
        retrieve_and_plot_shop_analysis(
            start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
        )
    )
    constructor = ApiUriConstructor(
        BASE_ADDRESS, "analysis", 1762300000, 1762470001, 541100015
    )
    res = constructor.build_uri("shops/cleaning/detail")
    print(res)
