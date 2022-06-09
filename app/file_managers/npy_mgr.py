import os
import pandas as pd

from app.misc.Logger import Logger


class NpyManager():

    logger = Logger.get_logger(__name__)
    
    def __init__(self, name):
        self.__save_file = f'data/{name}.h5'
        self.__data_file = pd.HDFStore(self.__save_file, mode='a')
        self.__dataframe = self.__data_file['/a']


    def data(self, entry_name=None):
        if entry_name is None:
            return self.__dataframe
        
        return self.__dataframe.loc[entry_name]


    def append(self, entry_name, data):
        self.__data_file.close()
        data.to_hdf(self.__save_file, entry_name, append=True)       
        self.__data_file = pd.HDFStore(self.__save_file)
        self.__dataframe = self.__data_file['/a']


    def rewrite(self, md5, data):
        self.__data_file.close()
        data.to_hdf(self.__save_file, md5, append=False)
        self.__data_file = pd.HDFStore(self.__save_file)
        self.__dataframe = self.__data_file['/a']
        

    def close(self):
        self.__data_file.close()


    def is_empty(self):
        return len(self.__dataframe) == 0


    def is_entry_exist(self, entry_name):
        return entry_name in self.__dataframe.index


    def get_num_entries(self):
        return len(self.__dataframe.index)
        

    def get_entries(self):
        return [ key for key in self.__dataframe.groupby(level=0) ]


    def drop(self):
        self.__data_file.close()
        os.remove(self.save_file)
        self.__data_file = pd.HDFStore(self.__save_file)
        self.__dataframe = self.__data_file['/a']   


score_data_obj = NpyManager('score_data')

