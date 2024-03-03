# filename: apple_stock_plotter.py
from pydantic import BaseModel
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class AppleStockPlotter(BaseModel):
    """
    Description: AppleStockPlotter provides a set of functions to plot Apple stock data.
    """
    def plot_stock_price(self):
        # Calculate the date 1 year ago from today
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Format dates in YYYY-MM-DD format
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Fetch Apple stock data from Yahoo Finance
        apple_stock_data = yf.download('AAPL', start=start_date_str, end=end_date_str)
        
        # Plot the closing prices
        plt.figure(figsize=(10, 6))
        plt.plot(apple_stock_data['Close'], label='Apple Stock Price')
        plt.title('Apple Stock Price (1 Year)')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.show()

# Example usage
if __name__ == "__main__":
    plotter = AppleStockPlotter()
    plotter.plot_stock_price()
