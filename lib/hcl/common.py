##
##

import attr
from typing import Union
from attr.validators import instance_of as io
from typing import Iterable


@attr.s
class Build(object):
    build = attr.ib(validator=io(dict))

    @classmethod
    def from_config(cls, json_data: dict):
        return cls(
            json_data.get("build"),
            )


@attr.s
class Entry(object):
    versions = attr.ib(validator=io(Iterable))

    @classmethod
    def from_config(cls, distro: str, json_data: dict):
        return cls(
            json_data.get(distro),
            )


@attr.s
class Variable(object):
    variable = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, value: Union[str, list], description: str):
        if type(value) == list:
            v_type: str = "list(string)"
        else:
            v_type: str = "string"
        return cls(
            {name: [
                {
                    "default": value,
                    "description": description,
                    "type": v_type
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__['variable']


@attr.s
class Variables(object):
    variable = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, variable: dict):
        self.variable.update(variable)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class ResourceBlock(object):
    resource = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.resource.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NodeBuild(object):
    node_block = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            [
                entry
            ]
        )

    def as_name(self, name: str):
        response = {name: self.__dict__['node_block']}
        return response


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
    def build(cls):
        return cls(
            {}
        )

    def add(self, var_name: str, var_value: str):
        self.local.update({var_name: var_value})
        return self

    @property
    def as_dict(self):
        return self.__dict__['local']


@attr.s
class NodeMain(object):
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
class NullResource(object):
    null_resource = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, element: dict):
        self.null_resource.update(element)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NullResourceBlock(object):
    resource_block = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            [
                entry
            ]
        )

    def as_name(self, name: str):
        response = {name: self.__dict__['resource_block']}
        return response


@attr.s
class NullResourceBody(object):
    elements = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, element: dict):
        self.elements.update(element)
        return self

    @property
    def as_dict(self):
        return self.__dict__['elements']


@attr.s
class Connection(object):
    elements = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, element: dict):
        self.elements.update(element)
        return self

    @property
    def as_dict(self):
        response = {"connection": [self.__dict__['elements']]}
        return response


@attr.s
class ConnectionElements(object):
    host = attr.ib(validator=io(str))
    private_key = attr.ib(validator=io(str))
    type = attr.ib(validator=io(str))
    user = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, host: str, private_key_file: str, user: str):
        return cls(
            host,
            f"${{file({private_key_file})}}",
            "ssh",
            f"${{var.{user}}}"
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class DependsOn(object):
    depends_on = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, element: str):
        self.depends_on.append(element)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class ForEach(object):
    for_each = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, element: str):
        return cls(
            element
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Provisioner(object):
    provisioner = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, element: dict):
        self.provisioner.update(element)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class RemoteExec(object):
    elements = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, element: dict):
        self.elements.update(element)
        return self

    @property
    def as_dict(self):
        response = {"remote-exec": [self.__dict__['elements']]}
        return response


@attr.s
class InLine(object):
    inline = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, element: str):
        self.inline.append(element)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Triggers(object):
    triggers = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, name: str, value: str):
        self.triggers.update({name: value})
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Output(object):
    output = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, element: dict):
        self.output.update(element)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class OutputValue(object):
    value = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, element: str):
        self.value.update({"value": element})
        return self

    def as_name(self, name: str):
        response = {name: [self.__dict__['value']]}
        return response
