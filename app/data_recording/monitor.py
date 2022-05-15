import watchdog.observers
import watchdog.events
import os

from app.misc.Logger import Logger
from app.misc.utils import Utils


class Monitor(watchdog.observers.Observer):

    logger = Logger.get_logger(__name__)

    def __init__(self, osu_path):
        watchdog.observers.Observer.__init__(self)

        if not os.path.exists(osu_path):
            raise Exception(f'"{osu_path}" does not exist!')

        self.osu_path = osu_path
        self.monitors = {}
        self.start()


    def __del__(self):
        self.stop()   


    def create_replay_monitor(self, name, callback):
        replay_path = f'{self.osu_path}/Data/r'
        if not os.path.exists(replay_path):
            raise Exception(f'"{replay_path}" does not exist!')

        class EventHandler(watchdog.events.FileSystemEventHandler):
            def on_created(self, event): 
                if '.osr' not in event.src_path:
                    return

                try: callback(event.src_path)
                except Exception as e:
                    Monitor.logger.error(Utils.get_traceback(e, 'Error processing replay'))

        Monitor.logger.info(f'Created file creation monitor for {self.osu_path}/Data/r')
        self.monitors[name] = self.schedule(EventHandler(), replay_path, recursive=False)
