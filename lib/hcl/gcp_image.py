##

import attr
from attr.validators import instance_of as io


@attr.s
class GCPImageDataRecord(object):
    version = attr.ib(validator=io(str))
    image = attr.ib(validator=io(str))
    family = attr.ib(validator=io(str))
    user = attr.ib(validator=io(str))

    @classmethod
    def from_config(cls, json_data):
        return cls(
            json_data.get("version"),
            json_data.get("image"),
            json_data.get("family"),
            json_data.get("user"),
            )

    @classmethod
    def by_version(cls, distro: str, version: str, json_data: dict):
        distro_list = json_data.get(distro)
        version_data = next((i for i in distro_list if i['version'] == version), {})
        return cls(
            version_data.get("version"),
            version_data.get("image"),
            version_data.get("family"),
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
class GooglePlugin(object):
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
class GooglePluginSettings(object):
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
    account_file = attr.ib(validator=io(str))
    communicator = attr.ib(validator=io(str))
    disk_size = attr.ib(validator=io(int))
    image_name = attr.ib(validator=io(str))
    machine_type = attr.ib(validator=io(str))
    project_id = attr.ib(validator=io(str))
    source_image = attr.ib(validator=io(str))
    source_image_family = attr.ib(validator=io(str))
    ssh_timeout = attr.ib(validator=io(str))
    ssh_username = attr.ib(validator=io(str))
    zone = attr.ib(validator=io(str))
    image_labels = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, os_linux_type: str,
                  os_linux_release: str,
                  machine_type: str,
                  gcp_zone: str,
                  gcp_project: str,
                  gcp_account_file: str,
                  os_image_name: str,
                  os_image_family: str,
                  os_image_user: str,
                  cb_version: str):
        return cls(
            f"${{var.{gcp_account_file}}}",
            "ssh",
            50,
            f"cf-${{var.{os_linux_type}}}-${{var.{os_linux_release}}}-cbs-${{local.timestamp}}",
            f"{machine_type}",
            f"${{var.{gcp_project}}}",
            f"${{var.{os_image_name}}}",
            f"${{var.{os_image_family}}}",
            "1h",
            f"${{var.{os_image_user}}}",
            f"${{var.{gcp_zone}}}",
            {
                "name": f"${{format(\"%s-%s-%s\", var.{os_linux_type}, var.{os_linux_release}, replace(var.{cb_version}, \".\", \"_\"))}}",
                "release": f"${{var.{os_linux_release}}}",
                "type": f"${{var.{os_linux_type}}}",
                "version": f"${{replace(var.{cb_version}, \".\", \"_\")}}"
            }
        )

    @property
    def as_dict(self):
        return self.__dict__
