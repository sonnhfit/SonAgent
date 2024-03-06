from pydantic import BaseModel

class NumberPrinter(BaseModel):
    """
    NumberPrinter.print_numbers
    description: print from start to end
    args:
        start: int start number
        end: int end number
    """

    def print_numbers(self, start, end):
        rs = ""
        for i in range(start, end + 1):
            rs += str(i) + " "
        return rs

# Example usage
if __name__ == "__main__":
    printer = NumberPrinter()
    printer.print_numbers()