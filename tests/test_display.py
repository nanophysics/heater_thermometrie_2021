from pytest_util import AssertDisplay

def test_display_to_readable():
    readable = AssertDisplay.lines_to_readable(
        ["          16.1K", " HEATING", " OFF", " out of range", " 0 error count"]
    )
    expected = """
    |           16.1K |
    |  HEATING |
    |  OFF |
    |  out of range |
    |  0 error count |
"""
    if readable != expected:
        raise Exception(readable)


def test_display_from_readable():
    for readable in (
        """
    |           16.1K |
    |  HEATING |
    |  OFF |
    |  out of range |
    |  0 error count |
""",
        """    |           16.1K |
  |  HEATING |
        |  OFF |
    |  out of range |
    |  0 error count |""",
    ):
        lines = AssertDisplay.readable_to_lines(readable)
        lines_expected = [
            "          16.1K",
            " HEATING",
            " OFF",
            " out of range",
            " 0 error count",
        ]
        assert lines == lines_expected
