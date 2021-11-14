# Installation of Labber Driver for compact_2012

## Pathnames

Tag | Default | Comment
-- | -- | --
`<LABBERDIR>` | `C:\Program Files\Labber` | Labber installation directory
`<LABBERPY32>` | `C:\Program Files\Labber\python-labber-32` | Labber Python 32 bit
`<LABBERPY64>` | `C:\Program Files\Labber\python-labber` | Labber Python 64 bit
`<LABBERDRIVERS>` | `C:\Program Files\Labber\Drivers` | Labber drivers
`<LABBERLOCALDRIVERS>` | `C:\Users\maerki\Labber\Drivers` | Labber local drivers. `maerki` is the logged in user
`<GITBIN>` | `C:\Program Files\Git\bin` | Git binaries

Mapping Tag to Labber Preferences

Tag        | Labber Instrument Server, Menu Preferences
-- | --
`<LABBERDIR>` | Tab Advanced, Application Folder
`<LABBERDRIVERS>` | Tab Folders, Instrument Drivers
`<LABBERLOCALDRIVERS>` | Tab Folders, Local Drivers


## Prerequisits Python 3.9.7 64bit
https://www.python.org/ftp/python/3.9.7/python-3.9.7-amd64.exe
Windows 64bit msi installer
 - Add Python 3.9 to path
 - Customize
   - Uncheck: Python test suite
   - Uncheck: pylauncher
 - Advanced
   - Uncheck: Install for all users
   - `C:\Users\maerki\AppData\Local\Programs\Python\Python39`


Python packages installed
```bash
C:\Users\maerki\AppData\Local\Programs\Python\Python39\python.exe -m pip install --upgrade pip
C:\Users\maerki\AppData\Local\Programs\Python\Python39\python.exe -m pip install -r requirements.txt
```

### Labber 1.7.7 installed.

### Configure Labber to user Python 3.9.7

Windows explorer: Copy directory `<git>/doc_installation/multiproc-include-py39` to `C:\Program Files\Labber\python-labber\multiproc-include\py39`

*This this step is skipped, a error window will pop up ""Optimizer Error: No application found ad ...".*

Labber Measurement Windows -> Edit -> Preferences -> Advanced -> Python distribution -> `C:\Users\maerki\AppData\Local\Programs\Python\Python39\python.exe`

### Patch Python 3.9.7 for Labber

If the following patch is NOT applied, this message will be displayed on the measurement console:

cmd.exe: `"C:\Program Files\Labber\Program\InstrumentServer-Console.exe"`
```python
Process Simple Signal Generator - ssg:
Traceback (most recent call last):
  File "C:\Users\maerki\AppData\Local\Programs\Python\Python39\lib\multiprocessing\process.py", line 303, in _bootstrap
    self._parent_name, self._parent_pid, parent_sentinel)
AttributeError: 'Process' object has no attribute '_parent_name'
```

Patch file `C:\Users\maerki\AppData\Local\Programs\Python\Python39\Lib\multiprocessing\process.py`:


```python
def _bootstrap(self, parent_sentinel=None):
    ...
    # PATCH BEGIN
    print("Apply patch for Labber 1.7.7")
    try:
        self._parent_name
    except AttributeError:
        self._parent_name = f"Parent_{self._name}"
    # PATCH BEGIN
    _parent_process = _ParentProcess(
```



### git installed.

Navigate to https://git-scm.com/download/win and download "64-bit Git for Windows Setup". Currently, this is: [Git-2.32.0-64-bit.exe](https://github.com/git-for-windows/git/releases/download/v2.32.0.windows.1/Git-2.32.0-64-bit.exe).

![GIT A](images/installation_git_a.png "GIT A")

![GIT B](images/installation_git_b.png "GIT B")

![GIT C](images/installation_git_c.png "GIT C")

![GIT D](images/installation_git_d.png "GIT D")

![GIT E](images/installation_git_e.png "GIT E")

![GIT F](images/installation_git_f.png "GIT F")

![GIT G](images/installation_git_g.png "GIT G")

![GIT H](images/installation_git_h.png "GIT H")

## Install compact_2012 labber driver

### Clone git repository

Run `cmd.exe`:
```bash
cd C:\Users\maerki\Labber\Drivers
git clone https://github.com/nanophysics/compact_2012
cd compact_2012
```

### Install python requirements

Run `cmd.exe` below as **Administrator**.
```bash
cd C:\Users\maerki\Labber\Drivers\compact_2012\doc_installation

"C:\Program Files\Labber\python-labber\Scripts\pip.exe" install --force-reinstall --no-cache-dir -r requirements.txt
```

There will be some warnings about *PATH*. You may ignore them.

The last line should be `Successfully installed ... mpfshell2-100.9.13 ...`!

Above command will install the required python libraries in `C:\Program Files\Labber\python-labber` (Labber 64bit Python).

## Configure the compact_2012 in the Labber Instrument Server

Start the Labber Instrument Server and choose menu `Edit -> Add...`

![LABBER ADD](images/installation_labber_add.png "LABBER ADD")

## Update the compact_2012 driver and calibration data

The driver AND the calibration data is stored in the git repository located at `<LABBERLOCALDRIVERS>\compact_2012`.

Double click `<LABBERLOCALDRIVERS>\compact_2012\run_git_pull.bat` to pull the newest version.
