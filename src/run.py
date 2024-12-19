# Everything is put under __main__ so that the map architect
#  could load code without invoking the GUI
if __name__ == '__main__':
    if sys.platform.startswith('win'):
    import os, sys
    import multiprocessing

    is_win = sys.platform.startswith('win')
    is_exe = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    if is_win and is_exe:
        # See: https://stackoverflow.com/a/27694505
        multiprocessing.freeze_support()

    if not is_exe:
        # Add editable libs to path
        sys.path.append(f'{os.environ["VIRTUAL_ENV"]}{os.sep}src')

    from PyQt6 import QtWidgets

    from misc.Logger import Logger
    from app import App

    Logger.get_logger('core').debug('Starting app')

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(open('res/stylesheet.css').read())

    ex = App()
    sys.exit(app.exec())
