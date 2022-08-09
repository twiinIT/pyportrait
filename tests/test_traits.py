# Copyright (C) 2022, twiinIT
# SPDX-License-Identifier: BSD-3-Clause

from pyportrait import HasTraits, Trait, observe


class TestHasTraits:
    def test_observable_tag(self):
        class Test(HasTraits):
            my_value: int = Trait(10).tag(observable=True)
            count = 0

            def __init__(self):
                super().__init__()

            @observe(r"my_value")
            def _value_changed(self, change):
                self.count += 1

        t = Test()
        assert t.count == 0

        t.my_value = 11
        assert t.count == 1
