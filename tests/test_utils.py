from sonagent.utils.utils import hash_str


def test_hash_str():
    assert hash_str('test') == '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
