import sys
import pathlib

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).resolve().parent
DIRECTORY_WORKSPACE = DIRECTORY_OF_THIS_FILE.parent
FILE_PYTEST_INI = DIRECTORY_WORKSPACE / "setup.cfg"
assert FILE_PYTEST_INI.exists()


def pytest_sessionstart(session):
    sys.path.insert(0, str(DIRECTORY_WORKSPACE))
