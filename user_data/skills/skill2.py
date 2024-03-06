# filename: apple_stock_plotter.py
from pydantic import BaseModel
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class GetAppleStockPlotter(BaseModel):
    """
    GetAppleStockPlotter.stock_price
    description: get latest Apple stock price from yahoo finace.
    args:
    """
    def stock_price(self):
        # Calculate the date 1 year ago from today
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Format dates in YYYY-MM-DD format
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        # Fetch Apple stock data from Yahoo Finance
        apple_stock_data = yf.download('AAPL', start=start_date_str, end=end_date_str)
        return f"apple stock price {end_date_str} is: " + str(apple_stock_data['Close'][-1]) + " USD"

