# MultiTray

MultiTray is a simple Python script for showing one or more system tray icons.
You can easily change the tray icons from the commandline or shell scripts by
writing instructions to a named fifo pipe (special file on disk).

# Usage

    usage: multitray [-h] [--version] [-v] [-p PIPEPATH]

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      -v, --verbose         Verbosity. May be specified multiple times (-vvv)
      -p PIPEPATH, --pipepath PIPEPATH
                            Path to put the named pipe in.

Start MultiTray:

    $ ./multitray.py

A FIFO named pipe will appear:

    $ ls -l
    total 8
    prw------- 1 fboender fboender    0 Jun 23 08:44 multitray.fifo
    -rwxr-xr-x 1 fboender fboender 5143 Jun 23 08:44 multitray.py

You can write text to this pipe to modify the tray icons. The format is:

    <TRAY_NAME> <COMMAND> <PARAMS...>

The `TRAY_NAME` uniquely identifies each separate tray. There's no need to
create the trays, they'll be automatically created if they don't exist yet.

Examples:

    # Create a tray with name "myfirsticon" and set it's icon to a green PNG
    # image.
    $ echo "myfirsticon set-icon /home/fboender/icons/green.png" > multitray.info

    # Change the icon to red and add a tooltip
    $ echo "myfirsticon set-icon /home/fboender/icons/red.png" > multitray.info
    $ echo "myfirsticon set-tooltip The flobulator is not cromulent" > multitray.info

    # Hide the icon
    $ echo "myfirsticon hide" > multitray.info

    # Show the icon
    $ echo "myfirsticon show" > multitray.info

    # Remove the icon
    $ echo "myfirsticon remove" > multitray.info