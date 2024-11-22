from shiny import App, render, ui, reactive
from shinywidgets import render_altair, output_widget
import pandas as pd
import altair as alt
import json

app_ui = ui.page_fluid(
    ui.input_select(
        id = "type_subtype", 
        label = "Select Type and Subtype", 
        choices = []
    ),
    output_widget("chart_alert_map")
)

def server(input, output, session):
    # Load waze data
    @reactive.calc
    def df_top_alerts_maps():
        df = pd.read_csv("top_alerts_map.csv")
        return df

    # Create choices for selector
    # summarize sets of type and subtype
    @reactive.calc
    def df_choices():
        df = df_top_alerts_maps().groupby(
            ["updated_type", "updated_subtype"]
        ).size().reset_index()
        return df
    
    # define choices
    @reactive.effect
    def _():
        choices = [f"{t} - {s}" for t, s in zip(
            df_choices()["updated_type"],
            df_choices()["updated_subtype"]
        )]
        ui.update_select("type_subtype", choices = choices)

    # Save input from the selecter
    # chosen type
    @reactive.calc
    def type_chosen():
        if input.type_subtype() == None:
            result = "Accident" # Set default for loading time
        elif input.type_subtype() == "Road closed - Hazard": # Might be categorized as "Hazard" type erroneously by the criterion below
            result = "Road closed"
        else:
            for type in df_choices()["updated_type"].unique():
                if type in input.type_subtype():
                    result = type
                    break
        return result
    
    # chosen subtype
    @reactive.calc
    def subtype_chosen():
        if input.type_subtype() == None:
            result = "Major" # Set default for loading time
        else:
            result = input.type_subtype().replace(
                " - ", ""
            ).replace(
                type_chosen(), ""
            )
        return result                    

    # Create output from the input
    # create subset of waze df
    @reactive.calc
    def df_chosen():
        df = df_top_alerts_maps()[(
            df_top_alerts_maps()["updated_type"] == type_chosen()
        )&(
            df_top_alerts_maps()["updated_subtype"] == subtype_chosen()
        )]
        return df

    # set appropriate domain for chosen type and subtype
    @reactive.calc
    def domain():
        domain = [min(df_chosen()["count"]), max(df_chosen()["count"])]
        return domain

    # create scatter plot for number of alert
    @reactive.calc
    def chart_alert():
        chart = alt.Chart(df_chosen()).mark_point(
            color = "firebrick",
            filled = True
        ).encode(
            longitude = "longitude:Q",
            latitude = "latitude:Q",
            size = alt.Size(
                "count:Q", 
                scale = alt.Scale(
                    domain = domain()
                ), 
                legend = alt.Legend(
                    title = "Number of Alerts"
                )
            )
        ).properties(
            title = f"Top 10 Areas of '{input.type_subtype()}' Alerts Number",
            height = 300,
            width = 300
        )
        return chart

    # Create map
    # load geojson    
    @reactive.calc
    def geo_data():
        with open("chicago-boundaries.geojson") as f:
            chicago_geojson = json.load(f)
        geo_data = alt.Data(values = chicago_geojson["features"])
        return geo_data

    # create plot the map
    @reactive.calc    
    def chart_map():
        chart = alt.Chart(geo_data()).mark_geoshape(
            fill = "lightgray",
            stroke = "white"
        ).project(
            type = "equirectangular"
        )
        return chart

    # Create plot for output_widget
    # overlay the plots
    @render_altair
    def chart_alert_map():
        return chart_map() + chart_alert()

app = App(app_ui, server)
