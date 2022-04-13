#!/usr/bin/env python
# coding: utf-8

import os

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from bokeh.models.widgets import Div
from dotenv import load_dotenv
from loguru import logger

from postgres_db import DB
from streamlit_style import Style


@st.cache(persist=False)
def get_subjects():
    with psql.select('streamlit_tracks').connect() as db:
        return pd.read_sql('subjects', db)


@st.cache(persist=False)
def return_database():
    return DB(os.environ['AZURE_POSTGRES_DB_STRING'])


@st.cache(persist=False)
def get_simple_id(cat_name):
    with psql.select('streamlit_tracks').connect() as db:
        simple_id = db.execute(f'SELECT * FROM subjects WHERE cat_name = \''
                               f'{cat_name.lower()}\'').fetchall()[0][0]
    return simple_id


@st.cache(persist=False)
def select_data(date, simple_id):
    with psql.select('gps_data').connect() as db:
        df = pd.read_sql(
            f"SELECT timestamp_local, location_lat, location_long, gps_hdop "
            f"FROM {simple_id.lower()} WHERE timestamp_local::date = '{date}' "
            f"AND gps_hdop < 1.3;",
            db,
            parse_dates=['timestamp_local'])

    df = df[(df['location_lat'] >= np.percentile(df['location_lat'], 0.05))
            & (df['location_lat'] < np.percentile(df['location_lat'], 99.95)) &
            (df['location_long'] >= np.percentile(df['location_long'], 0.05)) &
            (df['location_long'] <= np.percentile(df['location_long'], 99.95))]

    df.reset_index(inplace=True)
    df.drop(columns=['index'], inplace=True)
    return df


def select_tiles(default_only=True):
    if default_only:
        return 'https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}'
    tiles_dict = {
        'Satellite only':
        'https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}',
        'Roadmap': 'https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
        'Terrain': 'https://mt0.google.com/vt/lyrs=p&hl=en&x={x}&y={y}&z={z}',
        'Altered roadmap':
        'https://mt0.google.com/vt/lyrs=r&hl=en&x={x}&y={y}&z={z}',
        'Hybrid': 'https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}'
    }
    selected_tiles = st.sidebar.selectbox('Map layer style',
                                          tuple(tiles_dict.keys()),
                                          key=1)
    return tiles_dict[selected_tiles]


@st.cache(persist=False)
def styles_dict_func(keys_only=False):
    styles_dict = {
        'Line': px.line_mapbox,
        'Scatter': px.scatter_mapbox,
        'Density': px.density_mapbox,
    }
    if keys_only:
        return tuple(styles_dict.keys())
    else:
        return styles_dict


def points_style():
    keys = styles_dict_func(keys_only=False)
    selected_style = st.sidebar.selectbox('Tracking points shape', keys, key=2)
    return selected_style


def density_slider():
    scale_max = st.sidebar.slider('Scale maximum', 0, 50, 10, 1)
    return scale_max


@st.experimental_singleton
def map_func(data, color, zoom, tiles, function, density_slider_value=10):
    styles_dict = styles_dict_func()
    kwargs = {
        'lat': 'lat',
        'lon': 'lon',
        'hover_name': 'time',
        'hover_data': ['time'],
        'zoom': zoom,
        'height': 500,
    }
    if function == 'Density':
        kwargs.update({
            'opacity': 0.6,
            'color_continuous_scale': px.colors.sequential.Rainbow,
            'color_continuous_midpoint': density_slider_value,
        })
    else:
        kwargs.update({'color_discrete_sequence': [color]})
    fig = styles_dict[function](data, **kwargs)
    fig.update_layout(mapbox_style="white-bg",
                      mapbox_layers=[{
                          "below": 'traces',
                          "sourcetype": "raster",
                          "sourceattribution": "Google Maps, ©2021 Google",
                          "source": [tiles]
                      }])
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


def set_footer():
    hide_streamlit_style = """<style> footer {visibility: hidden;} 
    footer::before { content:'© 2021 Cat Tracker 2.0 | NC State University & 
    NC Museum of Natural Sciences | Maintained by Mohammad Alyetama'; 
    visibility: visible; position: fixed; left: 1; right: 1; bottom: 0; 
    text-align: center; } </style> """
    return st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def local_css():
    st.markdown('<style>{}</style>'.format(style.highlight_css()),
                unsafe_allow_html=True)


def highlight(string, color, num=1):
    return f"<span class='highlight_{num} {color}'>{string}</span>"


@st.cache(persist=False)
def list_unique_dates(simple_id):
    with psql.select('gps_data').connect() as db:
        unique_dates = db.execute(
            f"SELECT DISTINCT timestamp_local::date FROM {simple_id.lower()}"
        ).fetchall()
        unique_dates = sorted([x[0] for x in unique_dates])
    return unique_dates


@st.cache(persist=False)
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')


def download_file_button(df):
    df = convert_df(df)
    st.sidebar.download_button(
        label="Download data as CSV",
        data=df,
        file_name='results.csv',
        mime='text/csv',
    )


def buttons():
    bt1, bt2 = st.columns(2)
    with bt1:
        if st.sidebar.button('Source code 💻'):
            js = "window.open('https://github.com/Biodiversity-CatTracker2" \
                 "/cattracker2-tracks') "
            html = f'<img src onerror="{js}">'
            div = Div(text=html)
            st.bokeh_chart(div)
    with bt2:
        if st.sidebar.button('Report a bug 🐛'):
            js = "window.open('mailto:malyeta@ncsu.edu?subject=Bug%20report" \
                 "%20(tracks.cattracker.app%2F)') "
            html = f'<img src onerror="{js}">'
            div = Div(text=html)
            st.bokeh_chart(div)


@st.cache(persist=True)
def add_logger():
    logger.add("logs.log")


def inject(snippet):
    with open(f'{os.path.dirname(st.__file__)}/static/index.html', 'r') as f:
        content = f.read()
        if content.find(snippet) == -1:
            index_ = content.index('<head>')
            new_content = content[:index_] + snippet + content[index_:]
            with open(f'{os.path.dirname(st.__file__)}/static/index.html',
                      'w') as f:
                f.write(new_content)


def main(cat_name):
    add_logger()
    simple_id = get_simple_id(cat_name)

    local_css()
    title = f'# GPS coordinates of <i>{highlight(cat_name, "catname", 2)}</i>'
    st.markdown(title, unsafe_allow_html=True)

    unique_dates = list_unique_dates(simple_id)
    row1_1, _ = st.columns((1, 2))
    with row1_1:
        date_selected = st.selectbox('Select a date (YYYY/MM/DD)',
                                     tuple(unique_dates))
    # LOAD DATA
    df = select_data(date_selected, simple_id)

    local_css()
    try:
        img_url = f'https://cattracker2.blob.core.windows.net/tracks/cats/{cat_name.lower()}.webp'
        requests.get(img_url)
        st.sidebar.image(img_url, caption=cat_name.capitalize())
        st.sidebar.markdown('---')
    except requests.ConnectionError as e:
        logger.critical(e)

    color = st.sidebar.color_picker('Tracking points color', '#C81E00')

    if len(df) == 0:
        st.warning(
            'There are no data points for the selected time range/date!\*'
        )  # noqa
    else:
        # midpoint = (np.average(df['location_lat']),
        #             np.average(df['location_long']))
        df = df.rename(columns={'location_lat': 'lat', 'location_long': 'lon'})
        df['time'] = df['timestamp_local'].dt.time
        df.sort_values(by=['time'], inplace=True)
        first_time_in_date = df.iloc[0, 0]
        last_time_in_date = df.iloc[-1, 0]
        df = df.astype({'time': 'string'})

        t = 'Showing tracking points between ' \
            f'{highlight(first_time_in_date, "green")} and ' \
            f'{highlight(last_time_in_date, "blue")}*'
        st.markdown(t, unsafe_allow_html=True)

        function = points_style()
        if function == 'Density':
            density_slider_value = density_slider()
        else:
            density_slider_value = None
        tiles = select_tiles(default_only=True)

        with st.container():
            m = map_func(df, color, 15.5, tiles, function,
                         density_slider_value)
            st.plotly_chart(m, use_container_width=True)
        note_hdop = "<sub><sup>\*Only high-quality data points are shown (*[" \
                    "HDOP](https://wikiless.org/wiki/Dilution_of_precision_(" \
                    "navigation)?lang=en)* < 1.3)</sup></sub> "
        st.markdown(note_hdop, unsafe_allow_html=True)
    return df


if __name__ == '__main__':
    st.set_page_config(page_title='Cattracker 2.0: Cats Tracks',
                       page_icon='🐈',
                       layout='wide',
                       initial_sidebar_state='auto',
                       menu_items={
                           'Report a bug':
                           'https://cattracker.org/report-a'
                           '-bug',
                           'About':
                           '#### [Cat Tracker 2.0]('
                           'https://cattracker.org/)\n '
                           '###### NC State University & NC Museum '
                           'of Natural Sciences\n'
                           'Maintained by [Mohammad Alyetama]('
                           'https://github.com/Alyetama)\n'
                           '---'
                       })

    load_dotenv()

    inject(
        """<script defer data-domain="tracks.cattracker.app" src="https://plausible.fcatus.app/js/plausible.js"></script>"""
    )

    set_footer()
    style = Style()
    ph_bt = st.empty()
    ph_bt.markdown(style.get_badges(), unsafe_allow_html=True)

    psql = return_database()
    subjects = get_subjects()
    ph_0 = st.empty()
    col1, _ = ph_0.columns([1, 3])
    with col1:
        ph = st.empty()
        selection = ph.text_input('Search your cat\'s name', '')
        assert selection.lower().capitalize(
        ) in [x[1].capitalize()
              for x in subjects.values if x[2] is False] + ['', None]

    if selection:
        ph.empty()
        ph_bt.empty()
        ph_0.empty()
        st.markdown("""
            <style>
            div.stButton > button:first-child {
                background-color: #44475a;
                color:#ffffff;
            }
            div.stButton > button:hover {
                background-color: #f8f8f2;
                color:#282a36;
                }
            </style>""",
                    unsafe_allow_html=True)

        if st.button('⬅️ Go back'):
            st.markdown('<meta http-equiv="refresh" content="0">',
                        unsafe_allow_html=True)

        out = main(selection)
        st.sidebar.markdown('---')

        # download_file_button(out)
        # st.sidebar.markdown('---')

        buttons()
