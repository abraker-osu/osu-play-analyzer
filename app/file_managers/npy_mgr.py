import os
import pandas as pd

from app.misc.Logger import Logger


class NpyManager():

    logger = Logger.get_logger(__name__)
    
    def __init__(self, name):
        self.__save_file = f'data/{name}.h5'
        self.__data_file = pd.HDFStore(self.__save_file)


    def data(self, entry_name=None):
        if entry_name is None:
            return self.__data_file
        
        return self.__data_file.select(entry_name)


    def append(self, entry_name, data):
        self.__data_file.close()
        data.to_hdf(self.__save_file, f'_{entry_name}', append=True)       
        self.__data_file = pd.HDFStore(self.__save_file)


    def rewrite(self, md5, data):
        self.__data_file.close()
        data.to_hdf(self.__save_file, f'_{md5}', append=False)
        self.__data_file = pd.HDFStore(self.__save_file)
        

    def close(self):
        self.__data_file.close()


    def is_empty(self):
        return len(self.__data_file) == 0


    def is_entry_exist(self, entry_name):
        return f'_{entry_name}' in self.__data_file.keys()


    def get_entries(self):
        # Drop the prefix '/_'
        return [ key[1:] for key in self.__data_file.keys() ]


    def drop(self):
        self.__data_file.close()
        os.remove(self.save_file)
        self.__data_file = pd.HDFStore(self.__save_file)   


score_data_obj = NpyManager('score_data')

