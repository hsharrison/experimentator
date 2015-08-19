from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from contextlib import contextmanager


class ClassSchema(metaclass=ABCMeta):
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def lookup_name(self):
        return lambda *a, **k: None

    def __call__(self):
        return self.lookup_name()(*self.args, **self.kwargs)

    @classmethod
    def from_str(cls, name):
        return cls(name)()

    @classmethod
    def from_iterable(cls, args):
        return cls(*args)()

    @classmethod
    def from_dict(cls, info):
        name = info.pop('name', None) or info.pop('function', None) or info.pop('class')
        return cls(name, **info)()

    @classmethod
    def from_any(cls, data):
        if isinstance(data, str):
            return cls.from_str(data)

        if isinstance(data, dict):
            return cls.from_dict(data)

        if isinstance(data, Iterable):
            return cls.from_iterable(data)

        raise TypeError('Cannot process {}'.format(data))
