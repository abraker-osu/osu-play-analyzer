import os
import pandas as pd

from app.misc.Logger import Logger


class NpyManager():
    
    INDEX_NAMES = ['MD5', 'TIMESTAMP', 'MODS', 'IDXS']

    logger = Logger.get_logger(__name__)
    class CorruptionError(Exception):
        
        def __init__(self):
            Exception.__init__(self)


    def __init__(self,  file_pathname):
        self.__save_file = file_pathname

        if not os.path.exists(self.__save_file):
            self.__data_file = None
            self.__dataframe = None
            return

        self.__data_file = pd.HDFStore(self.__save_file, mode='a')
        
        try: self.__dataframe = self.__data_file['/play_data']
        except KeyError:
            self.__data_file.close()
            raise NpyManager.CorruptionError

        if len(self.__dataframe.index[0]) != len(NpyManager.INDEX_NAMES):
            NpyManager.logger.info('Data needs reindexing. Please wait...')

            self.__dataframe.reset_index(inplace=True)
            self.__dataframe.set_index(NpyManager.INDEX_NAMES, inplace=True)

            # TODO: Figure out how to modify the h5 store itself to apply the reindex columns to file


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
            self.__data_file.append('play_data', data, data_columns=[ 'MD5', 'TIMESTAMP', 'MODS', 'IDX' ])
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

        # TODO: If it doesn't exist, it what is written here?
        # TODO: need to rewrite by timestamp and mod as well
        

    def close(self):
        if self.__data_file is None:
            return

        self.__data_file.close()


    def is_empty(self):
        if self.__dataframe is None:
            return True

        return len(self.__dataframe) == 0


    def is_entry_exist(self, md5, timestamp=None, mods=None):
        if self.__dataframe is None:
            return False

        is_md5       = md5 in self.__dataframe.groupby(level=0)
        is_timestamp = True if timestamp is None else (timestamp in self.__dataframe.groupby(level=1))
        is_mods      = True if mods      is None else (mods      in self.__dataframe.groupby(level=2))

        return is_md5 and is_timestamp and is_mods


    def get_file_pathname(self):
        return self.__save_file


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
        os.remove(self.__save_file)
        self.__data_file = pd.HDFStore(self.__save_file)


#score_data_obj = NpyManager('score_data')

