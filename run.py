import sys

from app.misc.Logger import Logger


from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from app import App


if __name__ == '__main__':
    Logger.get_logger('core').debug('Starting app')

    app = QApplication(sys.argv)
    app.setStyleSheet(open('stylesheet.css').read())
    
    ex = App()
    sys.exit(app.exec_())
