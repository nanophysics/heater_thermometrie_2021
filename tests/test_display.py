from pytest_util import AssertDisplay

def test_display_to_readable():
    readable = AssertDisplay.lines_to_readable(
        ["          16.1K", " HEATING", " OFF", " out of range", " errors 5   "]
    )
    expected = '''"""
        |           16.1K |
        |  HEATING |
        |  OFF |
        |  out of range |
        |  errors 5    |
"""
'''
    if readable != expected:
        raise Exception(f"{readable}")


def test_display_from_readable():
    for readable in (
        """
    |           16.1K |
    |  HEATING |
    |  OFF |
    |  out of range |
    |  errors 5    |
""",
        """    |           16.1K |
  |  HEATING |
        |  OFF |
    |  out of range |
    |  errors 5    |""",
    ):
        lines = AssertDisplay.readable_to_lines(readable)
        lines_expected = [
            "          16.1K",
            " HEATING",
            " OFF",
            " out of range",
            " errors 5   ",
        ]
        assert lines == lines_expected
