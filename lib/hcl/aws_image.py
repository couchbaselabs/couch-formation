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
class ImageBuild(object):
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
    def construct(cls, os_type: str, os_rev: str, provisioner: dict, source_name: str, node_name: str):
        return cls(
            f"cf-{os_type}-{os_rev}-ami",
            provisioner,
            [f"source.{source_name}.{node_name}"]
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


@attr.s
class ShellElements(object):
    environment_vars = attr.ib(validator=io(list))
    inline = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, env_vars: list, shell_cmds: list):
        return cls(
            env_vars,
            shell_cmds
        )

    @property
    def as_dict(self):
        return self.__dict__


##
@attr.s
class Source(object):
    source = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            entry
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class SourceType(object):
    source_type = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            entry
        )

    def as_key(self, key):
        response = {key: self.__dict__['source_type']}
        return response


@attr.s
class NodeType(object):
    node_type = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            [
                entry
            ]
        )

    def as_key(self, key):
        response = {key: self.__dict__['node_type']}
        return response


@attr.s
class AMIFilter(object):
    filters = attr.ib(validator=io(dict))
    most_recent = attr.ib(validator=io(bool))
    owners = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, os_image_name: str, os_image_owner: str):
        return cls(
            {
                "name": f"${{var.{os_image_name}}}",
                "root-device-type": "ebs",
                "virtualization-type": "hvm"
            },
            True,
            [
                f"${{var.{os_image_owner}}}"
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NodeElements(object):
    ami_name = attr.ib(validator=io(str))
    instance_type = attr.ib(validator=io(str))
    region = attr.ib(validator=io(str))
    source_ami_filter = attr.ib(validator=io(list))
    ssh_username = attr.ib(validator=io(str))
    tags = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, os_linux_type: str,
                  os_linux_release: str,
                  instance_type: str,
                  region_var: str,
                  os_image_name: str,
                  os_image_owner: str,
                  os_image_user: str,
                  cb_version: str):
        return cls(
            f"cf-${{var.{os_linux_type}}}-${{var.{os_linux_release}}}-cbs-${{local.timestamp}}",
            f"{instance_type}",
            f"${{var.{region_var}}}",
            [AMIFilter.construct(os_image_name, os_image_owner).as_dict],
            f"${{var.{os_image_user}}}",
            {
                "Name": f"${{var.{os_linux_type}}}-${{var.{os_linux_release}}}-${{var.{cb_version}}}",
                "Release": f"${{var.{os_linux_release}}}",
                "Type": f"${{var.{os_linux_type}}}",
                "Version": f"${{var.{cb_version}}}"
            }
        )

    @property
    def as_dict(self):
        return self.__dict__
