from pydantic import BaseModel

class StringCapitalizer(BaseModel):
    """
    StringCapitalizer.capitalize_string
    - args: 
        input_string (str): The string to be capitalized.
    - returns: 
        str: The capitalized string.
    """

    def capitalize_string(self, input_string: str) -> str:
        # Capitalize input_string
        return input_string.upper()

if __name__ == "__main__":
    input_string = 'xin chào, mọi người!'
    capitalizer = StringCapitalizer()
    capitalized_string = capitalizer.capitalize_string(input_string)
    print(capitalized_string)