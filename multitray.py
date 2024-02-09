#!/usr/bin/env python3


import argparse
import os
import sys
import logging
import signal
import time
import shlex
from PyQt5.QtCore import QTimer, QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class PipeReader(QObject):
    """
    Create a named pipe (fifo) on disk and read from it.

    Data from the pipe is added to a buffer variable in this class. This class
    is runs as a QThread and the main QT thread reads from a buffer variable.
    """
    def __init__(self, pipepath):
        self.pipepath = pipepath
        if self.pipepath is None:
            self.pipepath = "multitray.fifo"
        super(PipeReader, self).__init__()

    def run(self):
        self.buffer = []

        try:
            os.mkfifo(self.pipepath, 0o600)
        except FileExistsError:
            pass

        with open(self.pipepath) as fifo:
            while True:
                time.sleep(0.1)
                for line in fifo:
                    self.buffer.append(line.strip())

    @pyqtSlot()
    def get_buffer(self):
        if len(self.buffer) > 0:
            tmp_buffer = self.buffer
            self.buffer = []
            return tmp_buffer


class TrayIcon():
    """
    Class to manage a single tray icon.
    """
    def __init__(self, name):
        self.name = name
        self.qt_icon_ref = None
        self.tray = QSystemTrayIcon()

    def set_icon(self, icon_path):
        self.icon_path = icon_path
        self.icon = QIcon(icon_path)
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)

    def blink(self):
        self.blink_status = 0
        self.orig_icon_path = self.icon_path

        self.blinker = QTimer()
        self.blinker.timeout.connect(self._blink)
        self.blinker.setInterval(500)
        self.blinker.start()

    def unblink(self):
        self.blinker.stop()
        del self.blinker

    def _blink(self):
        if self.blink_status == 0:
            self.set_icon(None)
            self.blink_status = 1
        else:
            self.set_icon(self.orig_icon_path)
            self.blink_status = 0


class Tray:
    """
    Main QT tray application.

    It reads from PipeReader and evaluates commands sent to this application
    via a named (FIFO) pipe, in order to manage the tray icons.
    """
    def __init__(self, pipepath):
        self.pipepath = pipepath
        self.tray_icons = {}
        self.cmd_handlers = {
            "set-icon": self._handle_cmd_set_icon,
            "set-tooltip": self._handle_cmd_set_toolip,
            "show": self._handle_cmd_show,
            "hide": self._handle_cmd_hide,
            "remove": self._handle_cmd_remove,
            "blink": self._handle_cmd_blink,
            "unblink": self._handle_cmd_unblink,
        }

        self.app = QApplication([])
        self.app.setQuitOnLastWindowClosed(False)

        self.thread = QThread()
        self.pipereader = PipeReader(self.pipepath)
        self.pipereader.moveToThread(self.thread)
        self.thread.started.connect(self.pipereader.run)

        self.thread.start()
        QTimer.singleShot(1, self._update)

        self.app.exec_()

    def _update(self):
        """
        Check named pipe for new commands.
        """
        buffer = self.pipereader.get_buffer()
        if buffer is not None:
            for cmd in buffer:
                self._handle_cmd(cmd)

        QTimer.singleShot(300, self._update)

    def _handle_cmd(self, cmd):
        """
        Handle commands read from the named pipe by dispatching them to the
        various _handle_cmd functions.
        """
        parts = shlex.split(cmd)
        if len(parts) < 1:
            sys.stderr.write("Not enough params in command: {}\n".format(cmd))
            return

        tray_icon_name = parts.pop(0)
        tray_icon = self.tray_icons.get(tray_icon_name, None)
        if tray_icon is None:
            tray_icon = TrayIcon(
                name = tray_icon_name
            )
            self.tray_icons[tray_icon_name] = tray_icon

        cmd = parts.pop(0)
        handler = self.cmd_handlers.get(cmd, None)
        if handler is None:
            sys.stderr.write("No such command: {}\n".format(cmd))
            return

        handler(tray_icon, parts)

    def _handle_cmd_set_icon(self, tray_icon, params):
        icon_path = params[0]
        if not os.path.exists(icon_path):
            sys.stderr.write("No such file or directory: {}\n".format(icon_path))
            return
        tray_icon.set_icon(icon_path)

    def _handle_cmd_set_toolip(self, tray_icon, params):
        tray_icon.tray.setToolTip(" ".join(params))

    def _handle_cmd_show(self, tray_icon, params):
        tray_icon.tray.setVisible(True)

    def _handle_cmd_hide(self, tray_icon, params):
        tray_icon.tray.setVisible(False)

    def _handle_cmd_remove(self, tray_icon, params):
        tray_icon.tray.setVisible(False)
        tray_icon_name = tray_icon.name
        del self.tray_icons[tray_icon_name]

    def _handle_cmd_blink(self, tray_icon, params):
        tray_icon.blink()

    def _handle_cmd_unblink(self, tray_icon, params):
        tray_icon.unblink()


signal.signal(signal.SIGINT, signal.SIG_DFL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="multitray")

    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s {}'.format("0.1"))

    parser.add_argument('-v', '--verbose',
                        action='count',
                        default=0,
                        help='Verbosity. May be specified multiple \
                              times (-vvv)')

    parser.add_argument('-p', '--pipepath',
                        metavar='PIPEPATH',
                        dest='pipepath',
                        type=str,
                        default=None,
                        help='Path to put the named pipe in.')

    args = parser.parse_args()

    # Configure application logging
    loglevel = logging.CRITICAL - ((args.verbose + 1) * 10)
    if loglevel > logging.ERROR:
        loglevel = logging.ERROR
    if loglevel < logging.DEBUG:
        loglevel = logging.DEBUG

    handler = logging.StreamHandler()
    fmt = '%(asctime)s %(levelname)8s %(name)s | %(message)s'
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    logger = logging.getLogger(__package__)
    logger.setLevel(loglevel)
    logger.addHandler(handler)

    tray = Tray(args.pipepath)
    tray.start()
