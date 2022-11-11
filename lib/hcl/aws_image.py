##

import attr
from attr.validators import instance_of as io


@attr.s
class ImageMain(object):
    elements = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, item: dict):
        self.elements.update(item)
        return self

    @property
    def as_dict(self):
        return self.__dict__['elements']


@attr.s
class Packer(object):
    packer = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            [
                entry
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class PackerElement(object):
    entry = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, element: dict):
        return cls(
            element
        )

    @property
    def as_dict(self):
        return self.__dict__['entry']


@attr.s
class RequiredPlugins(object):
    required_plugins = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, element: dict):
        return cls(
           [
                element
           ]
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AmazonPlugin(object):
    amazon = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, settings: dict):
        return cls(
            settings
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AmazonPluginSettings(object):
    source = attr.ib(validator=io(str))
    version = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, plugin: str, version: str):
        return cls(
            plugin,
            f"\u003e= {version}"
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Locals(object):
    locals = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            [
                entry
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class LocalVar(object):
    local = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, var_name: str, var_value: str):
        return cls(
            {var_name: var_value}
        )

    @property
    def as_dict(self):
        return self.__dict__['local']


@attr.s
class Build(object):
    build = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            [
                entry
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class BuildConfig(object):
    block = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, block: dict):
        return cls(
            block
        )

    @property
    def as_dict(self):
        return self.__dict__['block']


@attr.s
class BuildElements(object):
    name = attr.ib(validator=io(str))
    provisioner = attr.ib(validator=io(dict))
    sources = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, name: str, provisioner: dict, source: str):
        return cls(
            name,
            provisioner,
            source
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Shell(object):
    shell = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            [
                entry
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__
