import pandas as pd
import numpy as np
from requests.api import options
import streamlit as st
import yfinance as yf
from fbprophet import Prophet
from fbprophet.plot import plot_plotly, plot_components_plotly, plot_cross_validation_metric
from datetime import datetime, timedelta
from fbprophet.serialize import model_from_json
from model_tuning import load_data 
import pickle


def main():

    """
    Loads 'pickled' parameters and performance metrics from tuning and cross validation. Creates and fits model,
    then produces forecast with desiered forecast inputed via streamlit 'number_input' widget, and interval with inputed via radio buttons. The forecast along with
    latest performace metrics for a 14 day horizon are displayed via streamlit widgets.
    """

    #Set title and create sidebar with 'horizon' input widget
    st.title('ETH-USD Forecast')
    st.markdown('## Adaptive forecasting for the ETH-USD market')
    st.sidebar.header('General Information')
    st.sidebar.markdown('New data collected daily (close prices). Model tuning is also conducted daily to ensure the forecast is in-line with contemporary market conditions. \n' 
    'Currently, cross-validation suggests a maximum forecast horizon of 10-14 as being most suitable. Cross-validation performance metrics for a 6 - 14 day horizon are also updated daily.')
    st.sidebar.header('Forecast Horizon')
    horizon = st.sidebar.number_input(label='Input the number of days to be forecast', 
    min_value=1, max_value=None, value=14, step=7, help='Select forecast horizon to be displayed (default = 14 days)')
    st.sidebar.markdown('*NOTE: the +/- toggles will adjust the forecast in 7 day steps. For custom horizon, type number of days in and hit enter.*')
    st.sidebar.header('Interval Width')
    int_select = st.sidebar.radio(label='Please select confidence interval to be displayed', options=[.80, .85, .90, .95, .99], help=('Upper and lower interval to be displayed'), index=3)
    

    #Load data from Yahoo Finance (function defined in model_tuning.py), as well as 'pickled' parameters and cross-validation performance metrics
    data=load_data()
    params_in = open('tuned_params.pickle', 'rb')
    params = pickle.load(params_in)
    params_in.close()
    outlook_in = open('outlook.pickle', 'rb')
    outlook = pickle.load(outlook_in)
    outlook_in.close()
    outlook = outlook.astype({'Horizon': 'str'})

    #Build and fit Prohpet model with tuned 'changepoint_prior_scale' and 'seasonality_prior_scale' parameters 
    model=Prophet(
    seasonality_mode="multiplicative",
    yearly_seasonality=True,
    interval_width = int_select,
    changepoint_prior_scale=params['changepoint_prior_scale'][0],
    seasonality_prior_scale=params['seasonality_prior_scale'][0],
    changepoint_range=params['changepoint_range'][0]
    )

    model.fit(data)

    #Produce forecast and forecast plot employing the user-defined horizon
    future=model.make_future_dataframe(periods=horizon)
    forecast=model.predict(future)
    forecast_data = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    forecast_plot=plot_plotly(model, forecast_data, xlabel='Date', ylabel='Close Price (USD)')

    #Display forecast plot using streamlit widget 
    st.plotly_chart(forecast_plot, use_container_width=True)

    #Display cross-validation performance metrics using streamlit widget
    st.markdown('### Cross-validation performance metrics for a 6 - 14 day horizon')
    st.dataframe(outlook)
    st.markdown('*Data scource: Yahoo Finance*') 
    
#Execute 'main' function
if __name__ == '__main__':
    main()