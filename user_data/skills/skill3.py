from pydantic import BaseModel

class NumberPrinter(BaseModel):
    """
    NumberPrinter.print_numbers
    description: print from 1 to 10, in ra từ 1 đến 10
    args:
    """
    start: int = 1  # Giá trị bắt đầu mặc định
    end: int = 10   # Giá trị kết thúc mặc định
    
    def print_numbers(self):
        rs = ""
        for i in range(self.start, self.end + 1):
            rs += str(i) + " "
        return rs

# Example usage
if __name__ == "__main__":
    printer = NumberPrinter()
    printer.print_numbers()