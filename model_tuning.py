import pandas as pd
import itertools
import streamlit as st
import yfinance as yf
import pickle
from fbprophet import Prophet
from datetime import datetime, timedelta
from fbprophet.diagnostics import cross_validation, performance_metrics


def load_data():
    """
    Pull data from Yahoo Finance ranging from '2016-01-01' to the close price from the previous day.
    Data will cleaned and and organised in a way that it suitable for the Prophet model.
    """
    #Pull data using the yfinacne library
    start_date='2016-01-01'
    end_date=datetime.today() - timedelta(1)
    end_date=datetime.strftime(end_date, '%Y-%m-%d')
    yf_data=yf.download('ETH-USD',start_date, end_date)

    #Clean data and fill in missing values using a 'forward fill' method
    yf_data=yf_data.drop(['Open', 'High', 'Low', 'Adj Close', 'Volume'], axis=1)
    pd.date_range(start=start_date, end=end_date ).difference(yf_data.index)
    new_date_range=pd.date_range(start=start_date, end=end_date, freq="D")
    yf_data=yf_data.reindex(new_date_range, method='ffill')

    #Organise data in a manner that is suitable for use with Prophet
    prophet_df=yf_data.reset_index(level=0)
    prophet_df=prophet_df.rename({'index': 'ds', 'Close': 'y'}, axis=1)

    return prophet_df

def tune():
    """
    Tune a prophet model using pre-defined cutoff periods. Returns a dataframe with a single row containing
    optimal 'changepoint_prior_scale' value and 'seasonality_prior_scale' value.
    """
    #Define cutoff periods and parameters values to be searched
    cutoffs=pd.to_datetime(['2018-01-01', '2018-04-01', '2019-01-01', '2020-01-01'])
    param_grid={  
        'changepoint_prior_scale': [0.001, 0.01, 0.1, 0.5],
        'seasonality_prior_scale': [0.01, 0.1, 1.0, 10.0],
    }

    #Create list containing all parameter combinations
    all_params=[dict(zip(param_grid.keys(), v)) for v in itertools.product(*param_grid.values())]
    mae=[] 

    #Perfrom grid-search using mean absolute error (mae) as evaluation metric
    for params in all_params:
        m = Prophet(**params, seasonality_mode="multiplicative").fit(load_data()) 
        df_cv = cross_validation(m, cutoffs=cutoffs, horizon='60 days', parallel="processes")
        df_p = performance_metrics(df_cv, rolling_window=1)
        mae.append(df_p['mae'].values[0])

    #Create dataframe of results and return best perfroming parameters
    tuning_results=pd.DataFrame(all_params)
    tuning_results['mae']=mae
    tuning_results = tuning_results.sort_values(['mae'])[:1]
    tuning_results = tuning_results.reset_index(drop=True)
    
    return tuning_results

def cross_val(m):
   """
   Perform cross-validation and return dataframe of performance metrics
   """ 
   #Perform cross-validation (resulting in 46 model fits) and produce performance metrics
   df_cv=cross_validation(m, initial='730 days', period='30 days', horizon = '60 days')
   df_p=performance_metrics(df_cv)

   return df_p

def get_outlook(df):
    """
    Convert 'mae' and 'mape' into user-friendly evaluation metrics. Returns a dataframe with horizon, average +/- dollars, and average accuracy  
    """
    #Extract metrics of interest ('mae' and 'mape')
    forecast_outlook = df[['horizon', 'mae', 'mape']][:9]
    forecast_outlook = forecast_outlook.rename({'mae': '+/- Dollars (USD)', 'horizon': 'Horizon'}, axis = 1)

    #Create 'accuracy' metrics using 'mape' and produce final dataframe
    forecast_outlook['Accuracy (%)'] = forecast_outlook.apply(lambda row: 100 - row['mape']*100, axis = 1)
    forecast_outlook = forecast_outlook.drop('mape', axis = 1)
    forecast_outlook = forecast_outlook.round(2)

    return forecast_outlook

def main():
    """
    Perform grid-search to find best values for hyper-parameters 'changepoint_prior_scale' and 'seasonality_prior_scale'.
    Create model using tuned parameters and perform cross-validation to aquire performance metrics. Tuned parameters values 
    and performance metrics are then 'pickled'.
    """
    #Get tuned parameters and load data for model
    tuned_params = tune()
    data=load_data()

    #Create Prophet model object and fit to data
    model=Prophet(
    seasonality_mode="multiplicative",
    yearly_seasonality=True,
    interval_width=0.95,
    changepoint_prior_scale=tuned_params['changepoint_prior_scale'][0],
    seasonality_prior_scale=tuned_params['seasonality_prior_scale'][0]
    )

    model.fit(data)

    #Get performacne metrics from cross-validation
    outlook_res = get_outlook(cross_val(model))

    #Pickle tuned parameters
    pickle_params = open('tuned_params.pickle', 'wb')
    pickle.dump(tuned_params, pickle_params)
    pickle_params.close()

    #Pickle cross-validation performance metrics
    pickle_outlook = open('outlook.pickle', 'wb')
    pickle.dump(outlook_res, pickle_outlook)
    pickle_outlook.close()

#Execute 'main' function
if __name__ == '__main__':
    main()





