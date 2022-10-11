import os
import logging
import traceback

from app.misc.debug import log_debug


class Logger(logging.getLoggerClass()):

    unlisted = []

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level=logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s  %(asctime)s   [ %(name)s : %(threadName)s ] %(message)s')
        
        self.name = name

        self.sh = logging.StreamHandler()
        self.sh.setFormatter(formatter)
        self.sh.setLevel(logging.DEBUG)
        
        self.addHandler(self.sh)

        # \TODO: Maybe break up the logging file if it goes over 1MB
        #   get file size
        #   if over 1MB, then rename current logging file to '{start_date}_{end_date}_{logger_name}.log'
        #   cut-paste into logging folder named '{logger_name}'

        self.fh = logging.FileHandler(f'logs/{name}.log')
        self.fh.setFormatter(formatter)
        self.fh.setLevel(logging.INFO)
        
        self.addHandler(self.fh)


    def __del__(self):
        self.sh.close(); self.removeHandler(self.sh)
        self.fh.close(); self.removeHandler(self.fh)


    def info_debug(self, flag, msg):
        if not self.name in log_debug:
            return

        if flag and log_debug[self.name]:
            self.info(msg)


    def exception(self, msg):
        msg = msg.strip()
        msg += '\n' + traceback.format_exc()
        self.error(msg)


    @staticmethod
    def get_logger(name):
        name = name.split('.')[-1]

        logger = logging.getLogger(name)
        if name in log_debug:
            logger.sh.setLevel(logging.DEBUG if log_debug[name] else logging.INFO)
        else:
            if name not in Logger.unlisted:
                Logger.unlisted.append(name)
                Logger.get_logger('core').debug(f'Logger "{name}" not in log_debug. Adding to unlisted.')

            logger.sh.setLevel(logging.INFO)

        return logger


os.makedirs('logs', exist_ok=True)
logging.setLoggerClass(Logger)
