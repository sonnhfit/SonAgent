# filename: print_odd_numbers.py
from pydantic import BaseModel

class OddNumberPrinter(BaseModel):
    def print_odd_numbers(self):
        for number in range(1, 101):
            if number % 2 != 0:
                print(number)

# Tạo một instance của class và gọi phương thức để in ra các số lẻ
printer = OddNumberPrinter()
printer.print_odd_numbers()