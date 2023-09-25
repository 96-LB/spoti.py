from os import urandom
import time

import jwt

from constants import SECRET_KEY


DataT = str | bytes | int | float | bool | dict[str, 'DataT'] | list['DataT'] | tuple['DataT', ...]
class JWT:
    _data: dict[str, DataT]
    
    def __init__(self, _token: str = ..., /, **kwargs: DataT):
        self._data = kwargs
        self._data['__salt__'] = urandom(96).hex()
        if _token is not ...:
            self._data.update(jwt.decode(_token, SECRET_KEY, ['HS256']))
        if self.__time__:
            if not isinstance(self.__time__, (int, float)):
                raise ValueError(f'Invalid expiratinon time {self.__time__}.')
            if time.time() > self.__time__:
                raise ValueError(f'Token expired.')
    
    def __str__(self):
        self._data['__time__'] = time.time() + 300
        return jwt.encode(self._data, SECRET_KEY, 'HS256')
    
    def __getitem__(self, key: str) -> DataT:
        return self._data[key]
    
    def __getattr__(self, name: str) -> DataT | None:
        return self._data.get(name)
