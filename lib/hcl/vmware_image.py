##

import attr
from attr.validators import instance_of as io


@attr.s
class VMWareImageDataRecord(object):
    version = attr.ib(validator=io(str))
    image = attr.ib(validator=io(str))
    sw_url = attr.ib(validator=io(str))
    checksum = attr.ib(validator=io(str))
    type = attr.ib(validator=io(str))
    user = attr.ib(validator=io(str))
    vars = attr.ib(validator=io(str))
    hcl = attr.ib(validator=io(str))

    @classmethod
    def from_config(cls, json_data):
        return cls(
            json_data.get("version"),
            json_data.get("image"),
            json_data.get("sw_url"),
            json_data.get("checksum"),
            json_data.get("type"),
            json_data.get("user"),
            json_data.get("vars"),
            json_data.get("hcl"),
            )

    @classmethod
    def by_version(cls, distro: str, version: str, json_data: dict):
        distro_list = json_data.get(distro)
        version_data = next((i for i in distro_list if i['version'] == version), {})
        return cls(
            version_data.get("version"),
            version_data.get("image"),
            version_data.get("sw_url"),
            version_data.get("checksum"),
            version_data.get("type"),
            version_data.get("user"),
            version_data.get("vars"),
            version_data.get("hcl"),
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
class VMWarePlugin(object):
    vmware = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, settings: dict):
        return cls(
            settings
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VMWarePluginSettings(object):
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
    CPU_hot_plug = attr.ib(validator=io(bool))
    CPUs = attr.ib(validator=io(int))
    RAM = attr.ib(validator=io(str))
    RAM_hot_plug = attr.ib(validator=io(bool))
    boot_command = attr.ib(validator=io(list))
    boot_order = attr.ib(validator=io(str))
    boot_wait = attr.ib(validator=io(str))
    cdrom_type = attr.ib(validator=io(str))
    cluster = attr.ib(validator=io(str))
    communicator = attr.ib(validator=io(str))
    convert_to_template = attr.ib(validator=io(str))
    cpu_cores = attr.ib(validator=io(str))
    datacenter = attr.ib(validator=io(str))
    datastore = attr.ib(validator=io(str))
    disk_controller_type = attr.ib(validator=io(list))
    firmware = attr.ib(validator=io(str))
    folder = attr.ib(validator=io(str))
    guest_os_type = attr.ib(validator=io(str))
    http_content = attr.ib(validator=io(dict))
    http_port_max = attr.ib(validator=io(int))
    http_port_min = attr.ib(validator=io(int))
    insecure_connection = attr.ib(validator=io(bool))
    ip_wait_timeout = attr.ib(validator=io(str))
    iso_checksum = attr.ib(validator=io(str))
    iso_url = attr.ib(validator=io(str))
    network_adapters = attr.ib(validator=io(list))
    notes = attr.ib(validator=io(str))
    password = attr.ib(validator=io(str))
    remove_cdrom = attr.ib(validator=io(bool))
    shutdown_command = attr.ib(validator=io(str))
    shutdown_timeout = attr.ib(validator=io(str))
    ssh_password = attr.ib(validator=io(str))
    ssh_port = attr.ib(validator=io(int))
    ssh_timeout = attr.ib(validator=io(str))
    ssh_username = attr.ib(validator=io(str))
    storage = attr.ib(validator=io(list))
    tools_upgrade_policy = attr.ib(validator=io(bool))
    username = attr.ib(validator=io(str))
    vcenter_server = attr.ib(validator=io(str))
    vm_name = attr.ib(validator=io(str))
    vm_version = attr.ib(validator=io(int))

    @classmethod
    def construct(cls, os_linux_type: str,
                  os_linux_release: str,
                  boot_command: list,
                  http_content: dict,
                  vsphere_cluster: str,
                  vsphere_datacenter: str,
                  vsphere_datastore: str,
                  vsphere_folder: str,
                  vsphere_network: str,
                  vsphere_username: str,
                  vsphere_password: str,
                  vsphere_hostname: str,
                  os_image_name: str,
                  os_image_user: str,
                  os_iso_checksum: str,
                  build_password: str,
                  vm_disk_size: str,
                  vm_guest_os_type: str):
        return cls(
            False,
            1,
            "8192",
            False,
            boot_command,
            "disk,cdrom",
            "5s",
            "sata",
            f"${{var.{vsphere_cluster}}}",
            "ssh",
            True,
            "4",
            f"${{var.{vsphere_datacenter}}}",
            f"${{var.{vsphere_datastore}}}",
            [
                "pvscsi"
            ],
            "bios",
            f"${{var.{vsphere_folder}}}",
            f"${{var.{vm_guest_os_type}}}",
            http_content,
            8099,
            8000,
            True,
            "20m",
            f"${{var.{os_iso_checksum}}}",
            f"${{var.{os_image_name}}}",
            [
                {
                    "network": f"${{var.{vsphere_network}}}",
                    "network_card": "vmxnet3"
                }
            ],
            "Built by Couch Formation",
            f"${{var.{vsphere_password}}}",
            True,
            f"echo '${{var.{build_password}}}' | sudo -S -E shutdown -P now",
            "15m",
            f"${{var.{build_password}}}",
            22,
            "30m",
            f"${{var.{os_image_user}}}",
            [
                {
                    "disk_size": f"${{var.{vm_disk_size}}}",
                    "disk_thin_provisioned": True
                }
            ],
            True,
            f"${{var.{vsphere_username}}}",
            f"${{var.{vsphere_hostname}}}",
            f"${{var.{os_linux_type}}}-${{var.{os_linux_release}}}-couchbase-${{local.timestamp}}",
            14
        )

    @property
    def as_dict(self):
        return self.__dict__
