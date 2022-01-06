import numpy as np

from app.data_recording.data import RecData


class _PlayData():

    SAVE_FILE = 'data/osu_performance_recording_v1.npy'

    try: 
        data_file = open(SAVE_FILE, 'rb+')
        data = np.load(data_file, allow_pickle=False)
    except FileNotFoundError:
        print('Data file not found. Creating...')

        data = np.asarray([])
        np.save(SAVE_FILE, np.empty((0, RecData.NUM_COLS)), allow_pickle=False)
        
        data_file = open(SAVE_FILE, 'rb+')
        data = np.load(data_file, allow_pickle=False)

    @staticmethod
    def save_data(data):
        _PlayData.data_file.close()

        _PlayData.data = np.insert(_PlayData.data, 0, data, axis=0)
        np.save(_PlayData.SAVE_FILE, _PlayData.data, allow_pickle=False)

        # Now reopen it so it can be used
        _PlayData.data_file = open(_PlayData.SAVE_FILE, 'rb+')
        _PlayData.data = np.load(_PlayData.data_file, allow_pickle=False)


PlayData = _PlayData()