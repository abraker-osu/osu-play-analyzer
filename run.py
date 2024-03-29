# Everything is put under __main__ so that the map architect
#  could load code without invoking the GUI
if __name__ == '__main__':
    import sys
    from PyQt5 import QtWidgets

    from app.misc.Logger import Logger
    from app.app import App


    Logger.get_logger('core').debug('Starting app')

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(open('stylesheet.css').read())
    
    ex = App()
    sys.exit(app.exec_())
