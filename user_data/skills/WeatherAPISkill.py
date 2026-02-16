from pydantic import BaseModel

from sonagent.rpc import IOMsg


class WeatherAPISkill(BaseModel):
    """
    WeatherAPISkill.get_weather
    description: Get weather information for any city using OpenWeatherMap API
    args:
        - city: Name of the city to check weather
        - country_code: Two-letter country code (e.g., VN, US)
        - units: Temperature units: metric (Celsius) or imperial (Fahrenheit)
    """

    def get_weather(self, city: str, country_code: str, units: str):
        """
        Get weather information for any city using OpenWeatherMap API
        
        Args:
            city (str): Name of the city to check weather
            country_code (str): Two-letter country code (e.g., VN, US)
            units (str): Temperature units: metric (Celsius) or imperial (Fahrenheit)
        
        Returns:
            Result of the operation
        """
        import os
        # In a real implementation, you would use an API key from environment
        # api_key = os.environ.get('OPENWEATHER_API_KEY', 'demo-key')
        api_key = 'demo-key'

        # Construct API URL
        location = f"{city},{country_code}"
        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units={units}"

        # In a real implementation, you would make the actual API call:
        # import requests
        # response = requests.get(url)
        # weather_data = response.json()

        # For this demo, we'll return the URL that would be called
        result = f"Weather API endpoint: {url}\n"
        result += f"City: {city}, Country: {country_code}\n"
        result += f"Units: {units}\n"
        result += "In production, this would fetch real weather data."

        IOMsg.send_msg(result)
        return result

# Example usage
if __name__ == "__main__":
    skill = WeatherAPISkill()
    result = skill.get_weather(city="city_value", country_code="country_code_value", units="units_value")
    print(result)
