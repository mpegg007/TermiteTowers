uname -a                       # kernel name, version, architecture
lsb_release -a                 # distribution name and version (Linux)
sw_vers                        # macOS version (if on macOS)

echo $SHELL                    # path to your login shell
basename $SHELL                # shell name (bash, zsh, fish…)
$SHELL --version              # version info for that shell

which python                   # path to python interpreter
python --version              # Python version

which python3
python3 --version

echo $VIRTUAL_ENV             # full path to active virtualenv
which python

devpi-server --version        # devpi-server version
devpi --version               # devpi client version
