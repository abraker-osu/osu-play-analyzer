import sys
import multiprocessing


# Everything is put under __main__ so that the map architect
#  could load code without invoking the GUI
if __name__ == '__main__':
    if sys.platform.startswith('win'):
        # See: https://stackoverflow.com/a/27694505
        multiprocessing.freeze_support()

    from PyQt6 import QtWidgets

    from misc.Logger import Logger
    from app import App

    Logger.get_logger('core').debug('Starting app')

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(open('res/stylesheet.css').read())

    ex = App()
    sys.exit(app.exec())
