import logging
import re

logger = logging.getLogger(__name__)


def rewrite_code_post_process(response_content):
    code = str(response_content)
    logger.info("---------------")
    logging.info(f"Rewrite Python Code: {code}")
    logger.info("---------------")

    # get ```python ``` block
    try:
        pattern = r'```python(.*?)```'
        matches = re.findall(pattern, code, re.DOTALL)
        string_a = ""
        for match in matches:
            string_a = match.strip()
        python_code = string_a

    except Exception as e:
        logger.error(f"--- Error: {e}")
        python_code = code
    return python_code
