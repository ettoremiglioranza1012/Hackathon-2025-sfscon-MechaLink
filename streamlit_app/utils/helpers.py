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

WARNING_MESSAGE = "Ooops, it appears a problem occurred with this plot"
BASE_ADDRESS = "https://sfscon.tmkhosting.net"
# Serving layer API address (can be overridden with environment variable)
SERVING_LAYER_ADDRESS = os.getenv("SERVING_LAYER_ADDRESS", "http://localhost:8000")

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


def get_shops_from_api(api_base_url: str | None = None) -> list[dict]:
    """
    Retrieve list of shops from the API endpoint.
    
    Args:
        api_base_url: Optional base URL for the API. If not provided, uses SERVING_LAYER_ADDRESS.
    
    Returns:
        List of dictionaries containing shop information (shop_id, shop_name, etc.)
    """
    if api_base_url is None:
        api_base_url = SERVING_LAYER_ADDRESS
    
    try:
        # Try the serving layer endpoint first
        shops_endpoint = f"{api_base_url}/shops"
        response = req.get(shops_endpoint, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            # Handle different response formats
            if "shops" in data:
                return data["shops"]
            elif "data" in data and "list" in data["data"]:
                return data["data"]["list"]
            elif isinstance(data, list):
                return data
            else:
                return []
        else:
            # If serving layer fails, try the external API
            # Check if there's a shops endpoint in the external API
            external_shops_endpoint = f"{BASE_ADDRESS}/shops"
            if BASE_ADDRESS != api_base_url:
                response = req.get(
                    external_shops_endpoint,
                    headers={"x-key": API_KEY} if API_KEY else {},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and "list" in data["data"]:
                        return data["data"]["list"]
                    elif isinstance(data, list):
                        return data
            return []
    except Exception as e:
        # Return empty list on error - error handling is done in the UI
        return []


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

    # Create figure and plot with proper labels
    fig = px.line(
        df,
        x="task_time",
        y=["lively_count", "silent_count", "new_count"],
        title="Shop Activity Over Time",
        labels={
            "task_time": "Date/Time",
            "lively_count": "Lively Count",
            "silent_count": "Silent Count",
            "new_count": "New Count",
            "value": "Count",
            "variable": "Activity Type"
        },
    )
    
    # Update layout for better readability
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Count",
        legend_title="Activity Type",
        hovermode="x unified"
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True)


def retrieve_and_plot_shop_cleaning_detail(
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

    uri = constructor.build_uri("shops/cleaning/detail")
    retriever = ApiRetriever(
        # f"https://sfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["chart"])

    # Create figure and plot with proper labels
    fig = px.line(
        df,
        x="task_time",
        y=["running_task_count"],
        title="Cleaning Task Details - Running Tasks Over Time",
        labels={
            "task_time": "Date/Time",
            "running_task_count": "Running Tasks",
            "value": "Number of Tasks"
        },
    )
    
    # Update layout for better readability
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Number of Running Tasks",
        hovermode="x unified"
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True)


def retrieve_and_plot_shop_cleaning(
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

    uri = constructor.build_uri("shops/cleaning")
    retriever = ApiRetriever(
        # f"https://sfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["data"]["chart"])

    vars_to_plot = [
        "area",
        "duration",
        "power_consumption",
        "water_consumption",
    ]

    # Create figure and plot with proper labels
    fig = px.line(
        df,
        x="task_time",
        y=vars_to_plot[0],
        title="Cleaning Task - Area Coverage Over Time",
        labels={
            "task_time": "Date/Time",
            "area": "Area Cleaned (m²)",
            "value": "Area (m²)"
        },
    )
    
    # Update layout for better readability
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Area Cleaned (m²)",
        hovermode="x unified"
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True)
    else:
        print(df.head())


def retrieve_and_plot_shop_industrial(
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

    uri = constructor.build_uri("shops/industrial")
    retriever = ApiRetriever(
        # f"https://sfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["data"]["chart"])

    vars_to_plot = ["duration", "task_count", "mileage"]

    # Create figure and plot with proper labels
    fig = px.line(
        df,
        x="task_time",
        y=vars_to_plot[0],
        title="Industrial Tasks - Duration Over Time",
        labels={
            "task_time": "Date/Time",
            "duration": "Duration (minutes)",
            "value": "Duration (min)"
        },
    )
    
    # Update layout for better readability
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Duration (minutes)",
        hovermode="x unified"
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True)
    else:
        print(df.head())


def retrieve_and_plot_shop_delivery(
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

    uri = constructor.build_uri("shops/delivery")
    retriever = ApiRetriever(
        # f"https://sfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["data"]["chart"])

    vars_to_plot = ["task_count", "duration", "mileage", "table_count", "tray_count"]

    # Create figure and plot with proper labels
    fig = px.line(
        df,
        x="task_time",
        y=vars_to_plot[0],
        title="Delivery Tasks - Task Count Over Time",
        labels={
            "task_time": "Date/Time",
            "task_count": "Number of Tasks",
            "value": "Task Count"
        },
    )
    
    # Update layout for better readability
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Number of Delivery Tasks",
        hovermode="x unified"
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True)
    else:
        print(df.head())


def retrieve_and_plot_shop_cruise(
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

    uri = constructor.build_uri("shops/cruise")
    retriever = ApiRetriever(
        # f"https://sfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["data"]["chart"])

    vars_to_plot = ["duration", "task_count", "mileage"]

    # Create figure and plot with proper labels
    fig = px.line(
        df,
        x="task_time",
        y=vars_to_plot[0],
        title="Cruise Tasks - Duration Over Time",
        labels={
            "task_time": "Date/Time",
            "duration": "Duration (minutes)",
            "value": "Duration (min)"
        },
    )
    
    # Update layout for better readability
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Duration (minutes)",
        hovermode="x unified"
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True)
    else:
        print(df.head())


def retrieve_and_plot_shop_leading(
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

    uri = constructor.build_uri("shops/lead")
    retriever = ApiRetriever(
        # f"httpssfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["data"]["chart"])

    vars_to_plot = ["duration", "task_count", "mileage"]

    # Create figure and plot with proper labels
    fig = px.line(
        df,
        x="task_time",
        y=vars_to_plot[0],
        title="Leading Tasks - Duration Over Time",
        labels={
            "task_time": "Date/Time",
            "duration": "Duration (minutes)",
            "value": "Duration (min)"
        },
    )
    
    # Update layout for better readability
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Duration (minutes)",
        hovermode="x unified"
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True, key="lead")
    else:
        print(df.head())


def retrieve_and_plot_shop_solicit(
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

    uri = constructor.build_uri("shops/solicit")
    retriever = ApiRetriever(
        # f"httpssfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["data"]["chart"])

    vars_to_plot = ["duration", "task_count", "mileage"]

    # Create figure and plot with proper labels
    fig = px.line(
        df,
        x="task_time",
        y=vars_to_plot[0],
        title="Solicit Tasks - Duration Over Time",
        labels={
            "task_time": "Date/Time",
            "duration": "Duration (minutes)",
            "value": "Duration (min)"
        },
    )
    
    # Update layout for better readability
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Duration (minutes)",
        hovermode="x unified"
    )

    if __name__ != "__main__":
        st.plotly_chart(fig, use_container_width=True, key="solicit")
    else:
        print(df.head())


def retrieve_and_plot_shop_robots_general(
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
        "statistics",
        start_time_converted,
        end_time_converted,
        541100015,
        "hour",
    )

    uri = constructor.build_uri("robots/general")
    retriever = ApiRetriever(
        # f"httpssfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame(encoded_json["data"]["chart"])
    try:
        for el in encoded_json["data"]["chart"]:
            if el not in df.columns:
                df2 = pd.DataFrame(encoded_json[el])
                df = pd.concat([df, df2], axis=1)
    except Exception as e:
        raise Exception("Error occurred during DataFrame concatenation: ", e)

    vars_to_plot = ["bind_count", "active_count", "bind_rate", "active_rate"]

    # Create figure and plot with proper labels
    try:
        fig = px.bar(
            df,
            x="product_name",
            y=[vars_to_plot[0], vars_to_plot[1]],
            title="Robot Statistics - Bind and Active Counts by Model",
            labels={
                "product_name": "Robot Model",
                "bind_count": "Bound Robots",
                "active_count": "Active Robots",
                "value": "Count"
            },
            barmode="group"
        )
        
        # Update layout for better readability
        fig.update_layout(
            xaxis_title="Robot Model",
            yaxis_title="Number of Robots",
            legend_title="Metric",
            hovermode="x unified"
        )
        
        if __name__ != "__main__":
            st.plotly_chart(fig, use_container_width=True, key="robots_general")

    except Exception:
        st.warning(WARNING_MESSAGE)


def retrieve_and_plot_shop_robots_operations(
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
        "statistics",
        start_time_converted,
        end_time_converted,
        541100015,
        "hour",
    )

    uri = constructor.build_uri("robots/operations")
    retriever = ApiRetriever(
        # f"httpssfscon.tmkhosting.net/analysis/shops/general?start_time={start_time_converted}&end_time={end_time_converted}&shop_id={shop_id}&time_unit={time_unit}&timezone_offset={timezone_offset}",
        uri,
        API_KEY,
    )

    encoded_json = retriever.get_request()
    # return encoded_json["data"]["chart"]
    df = pd.DataFrame([encoded_json["data"]["summary"]])
    
    # Display the operations summary as a formatted dataframe
    st.subheader("Robot Operations Summary")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


if __name__ == "__main__":
    print(
        retrieve_and_plot_shop_robots_general(
            start_time=datetime(2025, 9, 1), end_time=(datetime(2025, 10, 31))
        )
    )

    if False:
        constructor = ApiUriConstructor(
            BASE_ADDRESS, "analysis", 1762300000, 1762470001, 541100015
        )
        res = constructor.build_uri("shops/cleaning/detail")
        print(res)
