"""
Befehle zum kopieren

COPY bevolkerung(dg, name, insgesamt, mannlich, weiblich)
FROM 'os.path.join(os.getcwd(), 'assets\bevolkerung.csv')
DELIMITER ';'
CSV HEADER;

COPY hochschule(hochschulname, typ, trager, bundesland, studis, precht, hrecht)
FROM 'os.path.join(os.getcwd(), 'assets\hochschule.csv')
DELIMITER ';'
CSV HEADER;

COPY wahl(bundesland, wahlberechtigte, wahlbeteiligung)
FROM 'os.path.join(os.getcwd(), 'assets\wahl.csv')
DELIMITER ';'
CSV HEADER;
"""

import psycopg2
from psycopg2 import Error
import plotly
import plotly.express as px
import json
import pandas as pd
import os
from dash import Dash, dcc, html, Input, Output

record=None

try:
    # Connect to an existing database
    connection = psycopg2.connect(user="postgres",
                                  password="1234",
                                  host="localhost",
                                  port="5432",
                                  database="test")

    cursor = connection.cursor()

    # Tabellen erstellen
    cursor.execute('''CREATE TABLE IF NOT EXISTS bevolkerung(dg SERIAL, name VARCHAR(150), insgesamt FLOAT, mannlich FLOAT, weiblich FLOAT, PRIMARY KEY(dg));''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS hochschule(hochschulname VARCHAR(200), typ VARCHAR(100), trager VARCHAR(100), bundesland VARCHAR(150), studis FLOAT, precht VARCHAR(10), hrecht VARCHAR(10), PRIMARY KEY(hochschulname));''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS wahl(bundesland VARCHAR(150), wahlberechtigte FLOAT, wahler FLOAT, wahlbeteiligung FLOAT, PRIMARY KEY(bundesland));''')


    # SQL query
    query = '''SELECT wahl.bundesland, SUM(studis) AS studierendenanzahl, (MAX(weiblich)*100)/MAX(insgesamt) AS frauenquote, (MAX(studis)*10000)/MAX(insgesamt) AS studierendenquote_pro_10000_einwohner, wahlbeteiligung
FROM bevolkerung
JOIN hochschule ON bevolkerung.name = hochschule.bundesland
JOIN wahl ON bevolkerung.name = wahl.bundesland
GROUP BY wahl.bundesland
ORDER BY SUM(studis) DESC;'''

    # Execute the query
    cursor.execute(query)
    record = cursor.fetchall()

    
# Error handling
except (Exception, Error) as error:
    print("Error while connecting to PostgreSQL", error)
finally:
    if connection:
        connection.commit()
        cursor.close()
        connection.close()
        print("PostgreSQL connection is closed")

# Load json file
with open(os.path.join(os.getcwd(), 'assets/1_sehr_hoch.geo.json')) as response:
    bundesland = json.load(response)

# Create data frame
df=pd.DataFrame(record, columns=['bundesland', 'studierendenanzahl', 'frauenquote', 'studierendenquote_pro_10000_einwohner', 'wahlbeteiligung'])

# Create list of all bundesländer
bundeslander = df['bundesland'].unique()

# Initialize the Dash app
app = Dash(__name__)

# App layout
app.layout = html.Div([
    html.H1("Bundesländerdaten"),
    dcc.Dropdown(
        id='color_type',
        options=[
            {'label': 'Studierendenanzahl', 'value': 'studierendenanzahl'},
            {'label': 'Studierendenquote', 'value': 'studierendenquote_pro_10000_einwohner'},
            {'label': 'Wahlbeteiligung', 'value': 'wahlbeteiligung'}
        ],
        value='studierendenanzahl',
        clearable=False
    ),
    dcc.Dropdown(
        id='bundesland_selector',
        options=[{'label': bundesland, 'value': bundesland} for bundesland in bundeslander],
        multi=True,
        value=list(bundeslander)  # All bundesländer are selected
    ),
    dcc.Graph(id='choropleth_map')
])

# Callback to update the choropleth map
@app.callback(
    Output('choropleth_map', 'figure'),
    [Input('color_type', 'value'),
     Input('bundesland_selector', 'value')]
)
def update_choropleth(color_type, selected_bundeslander):
    filtered_df = df[df['bundesland'].isin(selected_bundeslander)]
    fig = px.choropleth(filtered_df, geojson=bundesland, locations='bundesland', featureidkey='properties.name', color=color_type,
                        color_continuous_scale="Viridis",
                        hover_data=['studierendenanzahl', 'studierendenquote_pro_10000_einwohner', 'wahlbeteiligung', 'frauenquote']
                       )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

app.run_server(debug=True)