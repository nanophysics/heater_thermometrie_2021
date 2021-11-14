from pytest_util import AssertDisplay


def test_display_to_readable():
    readable = AssertDisplay.lines_to_readable(["          16.1K", " HEATING", " OFF", " out of range", " errors 5   "])
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
    for readable_expected in (
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
        """    |           16.1K |
  |  HEATING |
        |  OFF |
    |  out of range |
    | ? |""",
    ):
        #     readable_expected = """
        #         |           16.1K |
        #         |  HEATING |
        #         |  OFF |
        #         |  out of range |
        #         |  errors 5    |
        # """
        lines = [
            "          16.1K",
            " HEATING",
            " OFF",
            " out of range",
            " errors 5   ",
        ]
        # readable_expected = AssertDisplay.lines_to_readable(lines_expected)
        AssertDisplay.assert_equal(lines, readable_expected)
        # lines = AssertDisplay.readable_to_lines(readable)
        # assert lines == readable_expected
