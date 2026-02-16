from pydantic import BaseModel

from sonagent.rpc import IOMsg


class WeatherChecker(BaseModel):
    """
    WeatherChecker.weather_checker
    description: Check the weather in a specified city using an API
    args:
        - input_text: Input text for the operation
    """

    def weather_checker(self, input_text: str):
        """
        Check the weather in a specified city using an API
        
        Args:
            input_text (str): Input text for the operation
        
        Returns:
            Result of the operation
        """
        # TODO: Implement actual logic for: Check the weather in a specified city using an API
        result = f"Processing: {input_text}"
        IOMsg.send_msg(result)
        return result

# Example usage
if __name__ == "__main__":
    skill = WeatherChecker()
    result = skill.weather_checker(input_text="input_text_value")
    print(result)
