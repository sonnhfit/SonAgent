"""perfect_number_checker.py

A small, dependency-free utility for checking whether an integer is a *perfect number*.

A perfect number is a positive integer that is equal to the sum of its *proper divisors*
(all positive divisors less than the number itself).

This module provides:
- `is_perfect(n)`: check if an integer is perfect.
- `sum_proper_divisors(n)`: sum of proper divisors for a positive integer.

It also contains a simple interactive CLI when run as a script.

Example:
    >>> from tools.perfect_number_checker import is_perfect
    >>> is_perfect(6)
    True
    >>> is_perfect(28)
    True
    >>> is_perfect(12)
    False
"""

from __future__ import annotations

import logging
import math
from typing import Optional, Tuple


logger = logging.getLogger(__name__)


def _configure_default_logging() -> None:
    """Configure a sensible default logging setup.

    This only configures logging if the root logger has no handlers, which makes
    the module safe to import in larger applications without overriding their
    logging configuration.
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )


def sum_proper_divisors(n: int) -> int:
    """Compute the sum of proper divisors of `n`.

    Args:
        n: A positive integer.

    Returns:
        The sum of all positive divisors of `n` that are strictly less than `n`.

    Raises:
        ValueError: If `n` is less than 1.

    Notes:
        Uses factor pairing up to `sqrt(n)` for efficiency.
    """
    if n < 1:
        raise ValueError("n must be a positive integer")
    if n == 1:
        return 0

    total = 1  # 1 is a proper divisor for all n > 1
    limit = int(math.isqrt(n))

    for d in range(2, limit + 1):
        if n % d != 0:
            continue

        q = n // d
        if d != n:
            total += d
        if q != d and q != n:
            total += q

    return total


def is_perfect(n: int) -> bool:
    """Check whether `n` is a perfect number.

    Args:
        n: Integer to test.

    Returns:
        True if `n` is perfect, otherwise False.

    Notes:
        Perfect numbers are defined for positive integers only; for `n <= 1`
        this returns False.

    Logging:
        This function logs an INFO message whenever it is called.
    """
    _configure_default_logging()
    logger.info("is_perfect called with n=%s", n)

    if n <= 1:
        return False
    try:
        return sum_proper_divisors(n) == n
    except ValueError:
        return False


def parse_int(text: str) -> Tuple[Optional[int], Optional[str]]:
    """Parse an integer from user-provided text.

    Args:
        text: Raw text that should represent an integer.

    Returns:
        A tuple of (value, error_message). If parsing succeeds, error_message is None.
        If parsing fails, value is None.
    """
    try:
        return int(text.strip()), None
    except (TypeError, ValueError):
        return None, f"Invalid integer input: {text!r}"


def perfect_check_message(n: int) -> str:
    """Create a friendly message describing whether `n` is perfect.

    Args:
        n: Integer to test.

    Returns:
        A human-readable message.
    """
    return f"{n} is a perfect number." if is_perfect(n) else f"{n} is not a perfect number."


def interactive_cli() -> None:
    """Run an interactive command-line interface for perfect number checking."""
    _configure_default_logging()

    raw = input("Enter an integer to test for perfection: ")
    n, err = parse_int(raw)
    if err is not None:
        print(err)
        return

    print(perfect_check_message(n))


if __name__ == "__main__":
    _configure_default_logging()

    # Basic self-test cases
    tests = [
        -10,
        -1,
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        12,
        27,
        28,
        496,
        8128,
    ]
    for t in tests:
        print(f"{t}: {is_perfect(t)}")

    # Interactive mode
    interactive_cli()