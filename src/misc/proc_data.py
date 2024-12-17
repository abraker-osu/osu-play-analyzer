import base64
import json


class ProcData():

    def __init__(self):
        self.__stdout = ''
        self.__misc_data = {}


    def print(self, str=None):
        if str is None:
            print(self.__stdout, end='')
        else:
            self.__stdout += f'{str}\n'


    def data(self, key, data=None):
        if data is None:
            return self.__misc_data[key]
        else:
            self.__misc_data[key] = data


    def transmit(self):
        data_out = {}
        for key, data in self.__misc_data.items():
            if isinstance(data, str):
                data_out[key] = base64.b64encode(data.encode('UTF-8')).decode('latin1')
            
            # Other types not supported for now

        data_out['stdout'] = base64.b64encode(self.__stdout.encode('UTF-8')).decode('latin1')
        data_out = str(data_out).replace('\'', '\"')
        print(data_out)

        self.__stdout = ''
        self.__misc_data = {}


    def recieve(self, data):
        data = json.loads(data.decode('UTF-8'))

        self.__stdout = base64.b64decode(data['stdout']).decode('UTF-8')
        self.__misc_data = {
            key : base64.b64decode(val).decode('UTF-8')
            for key, val in data.items() if key != 'stdout'
        }
