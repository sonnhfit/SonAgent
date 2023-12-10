
def read_text_from_file(file_path: str) -> str:
    f = open(file_path, "r")
    f.close()
    return f.read()
