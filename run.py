if __name__ == '__main__':
    import sys
    import PyQt5

    from app.misc.Logger import Logger
    from app.app import App

    

    Logger.get_logger('core').debug('Starting app')

    app = PyQt5.QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(open('stylesheet.css').read())
    
    ex = App()
    sys.exit(app.exec_())
