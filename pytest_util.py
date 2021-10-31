import re
from typing import List

import pytest
import micropython_proxy

TEST_HW_SIMULATE = [
    pytest.param(""),
    pytest.param(micropython_proxy.HWSERIAL_SIMULATE, marks=pytest.mark.simulate),
]


class AssertDisplay:
    RE_LINE = re.compile(r"^\s*?\| (?P<line>.*?) \|\s*$")

    @staticmethod
    def lines_to_readable(lines: List[str]) -> str:
        assert isinstance(lines, list)
        d = '"""\n'
        for line in lines:
            d += f"        | {line} |\n"
        d += '"""\n'
        return d

    @staticmethod
    def readable_to_lines(readable: str) -> None:
        assert isinstance(readable, str)
        lines = []
        for line in readable.split("\n"):
            if line.strip() == "":
                continue
            match = AssertDisplay.RE_LINE.match(line)
            if match is None:
                raise Exception(f"Line ... '{line}'")
            lines.append(match.group("line"))
        assert len(lines) == 5
        return lines

    @staticmethod
    def _lines_equal(lines: List[str], lines_expected: List[str]):
        assert isinstance(lines, (list, tuple))
        assert isinstance(lines_expected, (list, tuple))
        for line, line_expected in zip(lines, lines_expected):
            if line_expected == "?":
                continue
            if line != line_expected:
                return False
        return True

    @staticmethod
    def assert_equal(lines: List[str], readable_expected: str):
        assert isinstance(lines, (list, tuple))
        lines_expected = AssertDisplay.readable_to_lines(readable_expected)
        if not AssertDisplay._lines_equal(lines, lines_expected):
            raise Exception(f"Expected:\n\n{AssertDisplay.lines_to_readable(lines)}\n")
