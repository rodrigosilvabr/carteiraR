import streamlit as st
import pandas as pd
import glob
import datetime as dt
import altair as alt
import plotly.graph_objects as go
#import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title('Carteira')
#####################################
#### Concatenate all excel files ####
#####################################
