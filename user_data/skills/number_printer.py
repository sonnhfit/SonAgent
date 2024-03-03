# filename: number_printer.py
from pydantic import BaseModel

class NumberPrinter(BaseModel):
    def print_numbers(self):
        for number in range(1, 11):
            print(number)

if __name__ == "__main__":
    np = NumberPrinter()
    np.print_numbers()