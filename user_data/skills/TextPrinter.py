from pydantic import BaseModel
from sonagent.rpc import IOMsg


class TextPrinter(BaseModel):
    """
    TextPrinter.print_text
    description: print text to the console
    args:
        - text: the text to print
    """

    def print_text(self, text):
        print(f"{text}")
        IOMsg.send_msg(text)
        
        return text

# Example usage
if __name__ == "__main__":
    printer = TextPrinter()
    printer.print_text("Hello, world!")