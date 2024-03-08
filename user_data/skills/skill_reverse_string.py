# Define the BaseModel class from pydantic
from pydantic import BaseModel

# Create a class to contain the reverse_string function
class ReverseString(BaseModel):
    """
    ReverseString.reverse_string
    description: Reverse the input string
    args:
        s: str input string to be reversed
    """
    def reverse_string(self, s):
        """
        Reverse the input string
        :param s: str input string to be reversed
        :return: str reversed input string
        """
        # Use slicing to reverse the string
        return s[::-1]

# Example usage within the if __name__ == "__main__" block
if __name__ == "__main__":
    example_string = "hello"
    # Create an instance of the ReverseString class
    reverse_string_instance = ReverseString()
    reversed_string = reverse_string_instance.reverse_string(example_string)
    print(f"Original string: {example_string}")
    print(f"Reversed string: {reversed_string}")