from pydantic import BaseModel

class NumberPrinter(BaseModel):
    """
    Description: NumberPrinter provides a set of functions to print numbers.
    ằng cách này, khi bạn chạy script này trực tiếp (ví dụ, `python your_script_name.py` từ dòng lệnh), Python sẽ đặt biến đặc biệt `__name__` thành `"__main__"`. Điều này có nghĩa là khối lệnh bên trong `if __name__ == "__main__":` sẽ được thực thi. Nếu bạn import script này vào một script khác, khối lệnh này sẽ không được thực thi, vì `__name__` sẽ được đặt thành tên của module (tên file) thay vì `"__main__"`.
    """
    start: int = 1  # Giá trị bắt đầu mặc định
    end: int = 10   # Giá trị kết thúc mặc định

    def print_numbers(self):
        for i in range(self.start, self.end + 1):
            print(i)

# Example usage
if __name__ == "__main__":
    printer = NumberPrinter()
    printer.print_numbers()