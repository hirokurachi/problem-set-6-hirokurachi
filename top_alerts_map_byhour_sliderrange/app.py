from shiny import App, render, ui, reactive
from shinywidgets import render_altair, output_widget
import pandas as pd
import altair as alt
import json
from datetime import date, time

app_ui = ui.page_fluid(
    ui.input_select(
        id="type_subtype",
        label="Select Type and Subtype",
        choices=[]
    ),
    ui.input_slider("hours_range", "Set range of hours",
                    0, 23, (0, 23), drag_range=True),
    output_widget("chart_alerts_map_byhour")
)
# Attribution: parameter "drag_range" refering to Shiny document (https://shiny.posit.co/py/api/core/ui.input_slider.html)


def server(input, output, session):
    # Load and store waze data
    @reactive.calc
    def df_top_alerts_map_byhour():
        """Create base df"""
        df = pd.read_csv("top_alerts_map_byhour.csv")
        df["hour_dt"] = pd.to_datetime(df["hour"], format="%H:%M")
        df["hour_dt"] = [x.time() for x in df["hour_dt"]]
        return df
        # Attribution: parameter "format" refering to Perplexity (https://www.perplexity.ai/search/from-shiny-import-app-render-u-Tt7cqT5WTmeh0z2CLZtU0A)

    # Create choices for selector
    @reactive.calc
    def df_choices():
        """Summarize sets of type and subtype"""
        df = df_top_alerts_map_byhour().groupby(
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

    # Save inputs from UI side
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

    @reactive.calc
    def hours_range():
        """Extract chosen range of hours from slider"""
        result = list(input.hours_range())
        return result

    # Create output from the inputs
    @reactive.calc
    def df_chosen():
        """Create subset of waze df"""
        df = df_top_alerts_map_byhour()[(
            df_top_alerts_map_byhour()["updated_type"] == type_chosen()
        ) & (
            df_top_alerts_map_byhour()["updated_subtype"] == subtype_chosen()
        ) & (
            df_top_alerts_map_byhour()["hour_dt"].between(
                time(hours_range()[0], 0), time(hours_range()[1], 0))
        )].drop("hour_dt", axis=1).head(10)
        return df

    @reactive.calc
    def domain():
        """Set appropriate domain for chosen type and subtype"""
        domain = [min(df_chosen()["count"]), max(df_chosen()["count"])]
        return domain

    @reactive.calc
    def chart_alerts_byhour():
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
        ).properties(
            title=f"Top 10 Areas of '{input.type_subtype()}' Alerts Number",
            height=300,
            width=300
        )
        return chart

    # Create plot for output_widget
    @render_altair
    def chart_alerts_map_byhour():
        """Overlay the plots, if there are observations which satisfy conditions"""
        if len(df_chosen()) == 0:
            return chart_map()
        else:
            return chart_map() + chart_alerts_byhour()


app = App(app_ui, server)
