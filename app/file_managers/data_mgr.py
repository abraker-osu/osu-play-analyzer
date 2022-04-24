import numpy as np

from app.misc.Logger import Logger
from app.data_recording.data import RecData


class _PlayData():

    SAVE_FILE = 'data/osu_performance_recording_v2.npy'
    logger = Logger.get_logger(__name__)

    try: 
        data_file = open(SAVE_FILE, 'rb+')
        data = np.load(data_file, allow_pickle=False)
    except FileNotFoundError:
        logger.info('Data file not found. Creating...')

        data = np.asarray([])
        np.save(SAVE_FILE, np.empty((0, RecData.NUM_COLS)), allow_pickle=False)
        
        data_file = open(SAVE_FILE, 'rb+')
        data = np.load(data_file, allow_pickle=False)

        if data.shape[1] != RecData.NUM_COLS:
            logger.info(
                '\n'+
                '============================================================\n' +
                'Warning: This version of the tool expects a different file format and may crash.' +
                f'Data file has wrong number of columns. Expected {RecData.NUM_COLS}, got {data.shape[1]}' +
                'You will need to delete "data/osu_performance_recording_v1.npy" and reimport plays.\n' +
                '============================================================\n' +
                '\n'
            )

    @staticmethod
    def add_to_data(data):
        _PlayData.data = np.insert(_PlayData.data, 0, data, axis=0)


    @staticmethod
    def save_data():
        _PlayData.data_file.close()
        np.save(_PlayData.SAVE_FILE, _PlayData.data, allow_pickle=False)

        # Now reopen it so it can be used
        _PlayData.data_file = open(_PlayData.SAVE_FILE, 'rb+')
        _PlayData.data = np.load(_PlayData.data_file, allow_pickle=False)


    @staticmethod
    def save_data_and_close():
        _PlayData.data_file.close()
        np.save(_PlayData.SAVE_FILE, _PlayData.data, allow_pickle=False)


PlayData = _PlayData()
