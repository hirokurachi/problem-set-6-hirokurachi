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
    ui.input_slider("hour_chosen", "Pick hour", 0, 23, 0),
    output_widget("chart_alert_map_byhour")
)

def server(input, output, session):
    # Load waze data
    @reactive.calc
    def df_top_alerts_maps_byhour():
        df = pd.read_csv("top_alerts_map_byhour.csv")
        return df

    # Create choices for selector
    # summarize sets of type and subtype
    @reactive.calc
    def df_choices():
        df = df_top_alerts_maps_byhour().groupby(
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

    # Save inputs from UI side
    # chosen type from selecter
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
    
    # chosen subtype from selecter
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

    # chosen hour from slider
    @reactive.calc
    def hour_chosen():
        result = f"{input.hour_chosen()}:00"
        return result

    # Create output from the inputs
    # create subset of waze df
    @reactive.calc
    def df_chosen():
        df = df_top_alerts_maps_byhour()[(
            df_top_alerts_maps_byhour()["updated_type"] == type_chosen()
        )&(
            df_top_alerts_maps_byhour()["updated_subtype"] == subtype_chosen()
        )&(
            df_top_alerts_maps_byhour()["hour"] == hour_chosen()
        )]
        return df

    # set appropriate domain for chosen type and subtype
    @reactive.calc
    def domain():
        domain = [min(df_chosen()["count"]), max(df_chosen()["count"])]
        return domain

    # create scatter plot for number of alert
    @reactive.calc
    def chart_alert_byhour():
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

    # create the map
    @reactive.calc    
    def chart_map():
        chart = alt.Chart(geo_data()).mark_geoshape(
            fill = "lightgray",
            stroke = "white"
        ).project(
            type = "equirectangular"
        ).properties(
            title = f"Top 10 Areas of '{input.type_subtype()}' Alerts Number",
            height = 300,
            width = 300
        )
        return chart

    # Create plot for output_widget
    # overlay the plots, if there are observations which satisfy conditions
    @render_altair
    def chart_alert_map_byhour():
        if len(df_chosen()) == 0:
            return chart_map()
        else:
            return chart_map() + chart_alert_byhour()

app = App(app_ui, server)
