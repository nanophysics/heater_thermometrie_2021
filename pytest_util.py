import re
from typing import List

import pytest
import micropython_proxy

TEST_HW_SIMULATE = [
    pytest.param(""),
    pytest.param(micropython_proxy.HWSERIAL_SIMULATE, marks=pytest.mark.simulate),
]


class AssertDisplay:
    RE_LINE = re.compile(f"^\s*?\| (?P<line>.*?) \|\s*$")

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
    def assert_equal(lines: List[str], readable_expected: str):
        lines_expected = AssertDisplay.readable_to_lines(readable_expected)
        if lines != lines_expected:
            raise Exception(f"Expected:\n\n{AssertDisplay.lines_to_readable(lines)}\n")
