from shiny import App, render, ui, reactive
from shinywidgets import render_altair, output_widget
import pandas as pd
import altair as alt
import json

app_ui = ui.page_fluid(
    ui.input_select(
        id="type_subtype",
        label="Select Type and Subtype",
        choices=[]
    ),
    output_widget("chart_alert_map")
)


def server(input, output, session):
    # Load and store waze data
    @reactive.calc
    def df_top_alerts_maps():
        """Create base df"""
        df = pd.read_csv("top_alerts_map.csv")
        return df

    # Create choices for selector
    @reactive.calc
    def df_choices():
        """Summarize sets of type and subtype"""
        df = df_top_alerts_maps().groupby(
            ["updated_type", "updated_subtype"]
        ).size().reset_index()
        return df

    @reactive.effect
    def _():
        """Define type-subtype choices"""
        choices = [f"{t} - {s}" for t, s in zip(
            df_choices()["updated_type"],
            df_choices()["updated_subtype"]
        )]
        ui.update_select("type_subtype", choices=choices)

    # Save input from the selecter
    @reactive.calc
    def type_chosen():
        """Extract chosen type from selecter input"""
        if input.type_subtype() == None:
            result = "Accident"  # Set default for loading time
        # Might be categorized as "Hazard" type erroneously by the criterion below
        elif input.type_subtype() == "Road closed - Hazard":
            result = "Road closed"
        else:
            for type in df_choices()["updated_type"].unique():
                if type in input.type_subtype():
                    result = type
                    break
        return result

    @reactive.calc
    def subtype_chosen():
        """Extract chosen subtype from selecter input"""
        if input.type_subtype() == None:
            result = "Major"  # Set default for loading time
        else:
            result = input.type_subtype().replace(
                " - ", ""
            ).replace(
                type_chosen(), ""
            )
        return result

    # Create output from the input
    @reactive.calc
    def df_chosen():
        """Create subset of waze df"""
        df = df_top_alerts_maps()[(
            df_top_alerts_maps()["updated_type"] == type_chosen()
        ) & (
            df_top_alerts_maps()["updated_subtype"] == subtype_chosen()
        )]
        return df

    @reactive.calc
    def domain():
        """Set appropriate domain for chosen type and subtype"""
        domain = [min(df_chosen()["count"]), max(df_chosen()["count"])]
        return domain

    @reactive.calc
    def chart_alert():
        """Create scatter plot for number of alert"""
        chart = alt.Chart(df_chosen()).mark_point(
            color="firebrick",
            filled=True
        ).encode(
            longitude="longitude:Q",
            latitude="latitude:Q",
            size=alt.Size(
                "count:Q",
                scale=alt.Scale(
                    domain=domain()
                ),
                legend=alt.Legend(
                    title="Number of Alerts"
                )
            )
        ).properties(
            title=f"Top 10 Areas of '{input.type_subtype()}' Alerts Number",
            height=300,
            width=300
        )
        return chart

    # Create map
    @reactive.calc
    def geo_data():
        """Load and store geojson"""
        with open("chicago-boundaries.geojson") as f:
            chicago_geojson = json.load(f)
        geo_data = alt.Data(values=chicago_geojson["features"])
        return geo_data

    @reactive.calc
    def chart_map():
        """Create the map"""
        chart = alt.Chart(geo_data()).mark_geoshape(
            fill="lightgray",
            stroke="white"
        ).project(
            type="equirectangular"
        )
        return chart

    # Create plot for output_widget
    @render_altair
    def chart_alert_map():
        """Overlay the plots"""
        return chart_map() + chart_alert()


app = App(app_ui, server)
