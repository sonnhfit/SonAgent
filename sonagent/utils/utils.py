import hashlib


def read_text_from_file(file_path: str) -> str:
    f = open(file_path, "r")
    f.close()
    return f.read()


def hash_str(string: str) -> str:
    sha = hashlib.sha256()
    sha.update(string.encode())
    return sha.hexdigest()


def hash_md5_str(string: str) -> str:
    m = hashlib.md5(string.encode('UTF-8'))
    return m.hexdigest()
