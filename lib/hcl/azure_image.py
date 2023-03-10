##

import attr
from attr.validators import instance_of as io


@attr.s
class AzureImageDataRecord(object):
    version = attr.ib(validator=io(str))
    type = attr.ib(validator=io(str))
    publisher = attr.ib(validator=io(str))
    offer = attr.ib(validator=io(str))
    sku = attr.ib(validator=io(str))
    user = attr.ib(validator=io(str))

    @classmethod
    def from_config(cls, json_data):
        return cls(
            json_data.get("version"),
            json_data.get("type"),
            json_data.get("publisher"),
            json_data.get("offer"),
            json_data.get("sku"),
            json_data.get("user"),
            )

    @classmethod
    def by_version(cls, distro: str, version: str, json_data: dict):
        distro_list = json_data.get(distro)
        version_data = next((i for i in distro_list if i['version'] == version), {})
        return cls(
            version_data.get("version"),
            version_data.get("type"),
            version_data.get("publisher"),
            version_data.get("offer"),
            version_data.get("sku"),
            version_data.get("user"),
        )


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
class AzurePlugin(object):
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
class AzurePluginSettings(object):
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
            f"cf-{os_type}-{os_rev}-image",
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
class NodeElements(object):
    image_offer = attr.ib(validator=io(str))
    image_publisher = attr.ib(validator=io(str))
    image_sku = attr.ib(validator=io(str))
    location = attr.ib(validator=io(str))
    managed_image_name = attr.ib(validator=io(str))
    managed_image_resource_group_name = attr.ib(validator=io(str))
    os_type = attr.ib(validator=io(str))
    use_azure_cli_auth = attr.ib(validator=io(bool))
    vm_size = attr.ib(validator=io(str))
    azure_tags = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, os_linux_type: str,
                  os_linux_release: str,
                  machine_type: str,
                  azure_location: str,
                  azure_resource_group: str,
                  os_type: str,
                  os_image_offer: str,
                  os_image_publisher: str,
                  os_image_sku: str,
                  cb_version: str):
        return cls(
            f"${{var.{os_image_offer}}}",
            f"${{var.{os_image_publisher}}}",
            f"${{var.{os_image_sku}}}",
            f"${{var.{azure_location}}}",
            f"cf-${{var.{os_linux_type}}}-${{var.{os_linux_release}}}-couchbase-${{local.timestamp}}",
            f"${{var.{azure_resource_group}}}",
            f"{os_type}",
            True,
            f"{machine_type}",
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
