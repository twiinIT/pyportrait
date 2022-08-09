# Copyright (C) 2022, twiinIT
# SPDX-License-Identifier: BSD-3-Clause

import abc
import inspect
import re

import reactivex as rx
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from reactivex import operators as ops


class Handler(abc.ABC):
    def __init__(self, name, filters=None, split_notifiers=None):
        self.name = name
        self.func = None
        self.filters = filters
        self.split_notifiers = split_notifiers

    def _init_call(self, func):
        self.func = func
        return self

    def __call__(self, *args, **kwargs):
        if self.func is not None:
            return self.func(*args, **kwargs)
        else:
            return self._init_call(*args, **kwargs)


class ObserveHandler(Handler):
    ...


def observe(name, filters=None, split_notifiers=True):
    return ObserveHandler(name, filters, split_notifiers)


class HasTraits(BaseModel):
    class Config:
        validate_assignment = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._subject = rx.Subject()
        self._observables = {
            f.name for f in self.__fields__.values() if f.field_info.extra.get("observable", False)
        }
        self._observers = dict()

        self._register_observers()

    def dispose(self):
        self._subject.on_completed()
        self._subject.dispose()

    def _register_observers(self):
        for key, m in inspect.getmembers(self):
            if isinstance(m, ObserveHandler):
                self.observe(key, m, m.name, m.filters, m.split_notifiers)

    def _handler_wrapper(self, handler):
        def f(*args, **kwargs):
            return handler(self, *args, **kwargs)

        return f

    def _add_notifier(self, handler_name, handler, pattern, filters=None):
        if filters:
            obs = self._subject.pipe(*filters)
        else:
            obs = self._subject.pipe(
                ops.filter(
                    lambda value: re.fullmatch(pattern, value["name"])
                    and value["new"] != value["old"]
                ),
            )
        obs.subscribe(on_next=self._handler_wrapper(handler))

        if handler_name in self._observers:
            self._observers[handler_name].append(obs)
        else:
            self._observers[handler_name] = [obs]

    def observe(self, handler_name, handler, pattern, filters=None, split_notifiers=True):
        if split_notifiers:
            names = [name for name in self._observables if re.fullmatch(pattern, name)]

            for name in names:
                self._add_notifier(handler_name, handler, name, filters)
        else:
            self._add_notifier(handler_name, handler, pattern, filters)

    def _notify(self, name, old, new):
        self._subject.on_next(dict(name=name, new=new, old=old))

    def __setattr__(self, name, value):
        try:
            old = super().__getattribute__(name)
            super().__setattr__(name, value)
            self._notify(name, old, value)
        except AttributeError:
            object.__setattr__(self, name, value)


class Trait(FieldInfo):
    def tag(self, **kwargs) -> "Trait":
        self.extra.update(**kwargs)
        return self
