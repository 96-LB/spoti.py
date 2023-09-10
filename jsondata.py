import json, os
from abc import ABC
from dataclasses import MISSING, Field, asdict, dataclass, fields
from functools import wraps

from types import GenericAlias
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Literal, TypeAlias, TypeGuard, TypeVar, Union, cast

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison
else:
    SupportsRichComparison = Any


T = TypeVar('T')
Bindable: TypeAlias = Union['JSONData', 'JSONData.AutoList[Any]', 'JSONData.AutoDict[Any]']


def _updater(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def wrapper(self: Bindable, *args: Any, suppress: bool = False, **kwargs: Any) -> T:
        result = func(self, *args, **kwargs)
        if not suppress:
            self.update()
        return result
    return wrapper


def isjsondata(hint: type | GenericAlias | None) -> TypeGuard[type['JSONData']]:
    if hint is None:
        return False
    
    if isinstance(hint, GenericAlias):
        return False
    
    if isinstance(hint, type(Literal['a', 'b'])):
        return False
    
    return issubclass(hint, JSONData)


class JSONData(ABC):
    '''Represents a dataclass which links its fields to a JSON file.'''
    
    FOLDER: str | None
    _instances: dict[str, 'JSONData']
    _fields: dict[str, Field[Any]]
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]
    
    def __init_subclass__(cls, folder: str | None = None, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        
        # prevents inheritence issues
        cls = dataclass(init=False)(cls) # type: ignore # can't seem to properly handle @dataclass
        cls.FOLDER = folder
        cls._instances = {}
        cls._fields = {field.name: field for field in fields(cls)} # type: ignore
    
    
    def __new__(cls, id: str = ''):
        # instances are cached by id
        if id and id in cls._instances:
            return cls._instances[id]
        
        # create a new instance and set its properties
        obj = super().__new__(cls)
        if id:
            cls._instances[id] = obj
        return obj
    
    
    def __init__(self, id: str = ''):
        if getattr(self, '__inited__', False):
            return
        
        self.id = id
        
        # load fields from json file, if it exists
        data: dict[str, Any] = {}
        if id:
            self._path = f'{self.FOLDER}/{id}.json'
            if os.path.exists(self._path):
                with open(self._path, 'r') as file:
                    try:
                        data = json.load(file)
                    except json.JSONDecodeError:
                        pass
        else:
            self._path = None
        
        for name, field in self._fields.items():
            value = None
            
            # prioritize the json file
            if name in data:
                value = data[name]
            elif field.default_factory is not MISSING:
                value = field.default_factory()
            elif field.default is not MISSING:
                value = field.default
            
            self.__setattr__(name, value, suppress=True)
        
        self.__inited__ = True
    
    
    def __setattr__(self, name: str, value: Any, *, suppress: bool = False):
        '''Binds objects and updates the linked JSON file.'''
        
        if name in self._fields:
            field = self._fields[name]
            
            value = JSONData.bind(value, self, hint=field.type)
        
        super().__setattr__(name, value)
        
        # update the json file if a field was set
        if name in self._fields and not suppress:
            self.update()
    
    
    def set(self, **kwargs: Any):
        '''Updates the specified fields of this object.'''
        
        # prevent updates from triggering on every field
        change = False
        for name, value in kwargs.items():
            if value is ...:
                continue
            
            self.__setattr__(name, value, suppress=True)
            if name in self._fields:
                change = True
        
        # only update once at the end
        if change:
            self.update()
        
        return self
    
    
    def update(self) -> None:
        '''Writes this object's fields to the linked JSON file.'''
        
        if self._path is not None:
            with open(self._path, 'w') as file:
                json.dump(self, file, default=asdict, indent=4)
    
    
    def to_json(self) -> str:
        return json.dumps(self, default=asdict, indent=4)
    
    
    def to_dict(self) -> dict[str, Any]:
        return json.loads(self.to_json())
    
    
    @staticmethod
    def bind(value: Any, obj: Bindable, hint: type | GenericAlias | None = None) -> Any:
        '''Converts objects to automatically updating types.'''
        
        # we rebuild a deep copy of json dataclass
        if isinstance(value, JSONData):
            hint = type(value)
            value = asdict(value)
        
        
        # do NOT make this an elif
        if isinstance(value, dict):
            # object should be interpreted as a json dataclass
            if isjsondata(hint):
                auto = hint().set(**value)
                auto.update = lambda: obj.update()
                value = auto
            
            # it's just a regular dictionary
            else:
                if isinstance(hint, GenericAlias) and hint.__origin__ is dict:
                    assert hint.__args__[0] is str
                    subhint = hint.__args__[1]
                else:
                    subhint = None
                
                
                value = cast(dict[str, Any], value) # ehh
                value = JSONData.AutoDict.from_dict(value, obj, hint=subhint)
        
        # this SHOULD be an elif
        elif isinstance(value, list):
            subhint = hint.__args__[0] if isinstance(hint, GenericAlias) and hint.__origin__ is list else None
            value = cast(list[Any], value) # ehh
            value = JSONData.AutoList.from_list(value, obj, hint=subhint)
        
        # null values represent empty json dataclasses
        elif value is None:
            if isjsondata(hint):
                value = hint()
                value.update = lambda: obj.update()
        
        
        return value
    
    
    class AutoDict(dict[str, T]):
        '''Dictionary which automatically updates its containing object when modified.'''
        
        
        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            self.obj: Bindable | None = None
            self.hint: type | GenericAlias | None = None
        
        
        @_updater
        def __setitem__(self, key: str, value: Any):
            value = JSONData.bind(value, self, hint=self.hint)
            super().__setitem__(key, value)
        
        
        @_updater
        def __delitem__(self, key: str):
            super().__delitem__(key)
        
        
        @_updater
        def pop(self, key: str, default: T = ...) -> T:
            if default is ...:
                return super().pop(key)
            else:
                return super().pop(key, default)
        
        
        @_updater
        def clear(self):
            super().clear()
        
        
        @_updater
        def popitem(self):
            return super().popitem()
        
        
        @_updater
        def setdefault(self, key: str, default: T):
            default = JSONData.bind(default, self, hint=self.hint)
            return super().setdefault(key, default)
        
        
        @_updater
        def __ior__(self, other: dict[str, T]):
            return super().__ior__(other)
        
        
        def update(self, *args: Any, **kwargs: Any):
            if args or kwargs:
                return super().update(*args, **kwargs)
            
            if self.obj is not None:
                self.obj.update()
        
        
        @staticmethod
        def from_dict(data: dict[str, T], obj: Bindable, hint: type | GenericAlias | None = None) -> 'JSONData.AutoDict[T]':
            autodict: JSONData.AutoDict[T] = JSONData.AutoDict()
            autodict.obj = obj
            autodict.hint = hint
            
            for key, value in data.items():
                autodict.__setitem__(key, value, suppress=True)
            
            return autodict
        
        
        def __repr__(self):
            return f'a{super().__repr__()}'
    
    
    class AutoList(list[T]):
        '''List which automatically updates its containing object when modified.'''
        
        
        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            self.obj: Bindable | None = None
            self.hint: type | GenericAlias | None = None
        
        
        @_updater
        def __setitem__(self, index: int, value: T):
            value = JSONData.bind(value, self, hint=self.hint)
            super().__setitem__(index, value)
        
        
        @_updater
        def __delitem__(self, index: int):
            super().__delitem__(index)
        
        
        @_updater
        def __iadd__(self, other: Iterable[T]):
            other = [JSONData.bind(x, self, hint=self.hint) for x in other]
            return super().__iadd__(other)
        
        
        @_updater
        def append(self, value: T):
            value = JSONData.bind(value, self, hint=self.hint)
            super().append(value)
        
        
        @_updater
        def insert(self, index: int, value: T):
            value = JSONData.bind(value, self, hint=self.hint)
            super().insert(index, value)
        
        
        @_updater
        def remove(self, value: T):
            super().remove(value)
        
        
        @_updater
        def pop(self, index: int = -1):
            return super().pop(index)
        
        
        @_updater
        def sort(self, key: Callable[[T], SupportsRichComparison], reverse: bool = False):
            super().sort(key=key, reverse=reverse)
        
        
        @_updater
        def reverse(self):
            super().reverse()
        
        
        @_updater
        def extend(self, lst: Iterable[T]):
            lst = [JSONData.bind(x, self, hint=self.hint) for x in lst]
            super().extend(lst)
        
        
        @_updater
        def clear(self):
            super().clear()
        
        
        def update(self):
            if self.obj is not None:
                self.obj.update()
        
        
        @staticmethod
        def from_list(data: list[T], obj: Bindable, hint: type | GenericAlias | None = None) -> 'JSONData.AutoList[T]':
            autolist: JSONData.AutoList[T] = JSONData.AutoList()
            autolist.obj = obj
            autolist.hint = hint
            
            for value in data:
                autolist.append(value, suppress=True)
            
            return autolist
        
        
        def __repr__(self):
            return f'a{super().__repr__()}'
