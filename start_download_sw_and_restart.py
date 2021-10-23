import pathlib

from micropython_interface import mp, HWTYPE_HEATER_THERMOMETRIE_2021

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent


def download_sw_and_restart():
    board = mp.pyboard_query.ConnectHwtypeSerial(
        product=mp.pyboard_query.Product.Pyboard,
        hwtype=HWTYPE_HEATER_THERMOMETRIE_2021,
        hwserial="20210601_01",
    )
    assert isinstance(board, mp.pyboard_query.Board)
    board.systemexit_hwtype_required(hwtype=HWTYPE_HEATER_THERMOMETRIE_2021)
    board.systemexit_firmware_required(min="1.14.0", max="1.14.0")

    # Download the source code
    board.mpfshell.sync_folder(
        DIRECTORY_OF_THIS_FILE / "src_micropython",
        FILES_TO_SKIP=["config_identification.py"],
    )

    board.mpfshell.soft_reset()
    fe = board.mpfshell.MpFileExplorer
    fe.exec("import main")


if __name__ == "__main__":
    download_sw_and_restart()
