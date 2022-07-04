import os
import pandas as pd

from app.misc.Logger import Logger


class NpyManager():

    logger = Logger.get_logger(__name__)
    
    def __init__(self, name):
        self.__save_file = f'data/{name}.h5'

        if os.path.exists(self.__save_file):
            self.__data_file = pd.HDFStore(self.__save_file, mode='a')
            self.__dataframe = self.__data_file['/play_data']
        else:
            self.__data_file = None
            self.__dataframe = None


    def data(self, md5=None):
        if self.__dataframe is None:
            return None

        if md5 is None:
            return self.__dataframe
        
        return self.__dataframe.loc[md5]


    def append(self, data):
        if self.__data_file is None:
            # Non existent, create it
            data.to_hdf(self.__save_file, key='play_data', mode='a', format='table')
            
            self.__data_file = pd.HDFStore(self.__save_file, mode='a')
            self.__dataframe = self.__data_file['/play_data']
        else:
            # Exists and can be appended to
            self.__data_file.append('play_data', data, data_columns=[ 'MD5', 'TIMESTAMP', 'IDX' ])
            self.__dataframe = self.__data_file['/play_data']


    def rewrite(self, md5, data):
        if self.__dataframe is None:
            # Non existent, create it
            data.to_hdf(self.__save_file, key='play_data', mode='a', format='table')
            
            self.__data_file = pd.HDFStore(self.__save_file, mode='a')
            self.__dataframe = self.__data_file['/play_data']
        else:
            # Exists and can be overwritten
            self.__dataframe.loc[md5] = data
        

    def close(self):
        if self.__data_file is None:
            return

        self.__data_file.close()


    def is_empty(self):
        if self.__dataframe is None:
            return True

        return len(self.__dataframe) == 0


    def is_entry_exist(self, md5, timestamp):
        if self.__dataframe is None:
            return False

        return (
            md5 in self.__dataframe.groupby(level=0) and
            timestamp in self.__dataframe.groupby(level=1)
        )


    def get_num_entries(self):
        if self.__dataframe is None:
            return 0

        return len(self.__dataframe.index)
        

    def get_entries(self):
        if self.__dataframe is None:
            return [ ]

        return [ key for key in self.__dataframe.groupby(level=0) ]


    def drop(self):
        if self.__data_file is None:
            return

        self.__data_file.close()
        os.remove(self.save_file)
        self.__data_file = pd.HDFStore(self.__save_file)


score_data_obj = NpyManager('score_data')

