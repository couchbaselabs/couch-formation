##
##

import attr
from attr.validators import instance_of as io


@attr.s
class TerraformElement(object):
    terraform = attr.ib(validator=io(list))

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
class RequiredProvider(object):
    required_providers = attr.ib(validator=io(list))

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
class AzureTerraformProvider(object):
    azurerm = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, source: str):
        return cls(
            {"source": source}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class ImageData(object):
    azurerm_image = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, image: str, resource_group: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{image}}}",
                    "resource_group_name": f"${{var.{resource_group}}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NSGData(object):
    azurerm_network_security_group = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, nsg: str, resource_group: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{nsg}}}",
                    "resource_group_name": f"${{var.{resource_group}}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class SubnetData(object):
    azurerm_subnet = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, for_each: str, subnet: str, resource_group: str, vnet: str):
        return cls(
            {f"{name}": [
                {
                    "for_each": f"${{var.{for_each}}}",
                    "name": f"${{each.value.{subnet}}}",
                    "resource_group_name": f"${{var.{resource_group}}}",
                    "virtual_network_name": f"${{var.{vnet}}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureProviderBlock(object):
    provider = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls):
        return cls(
            {"azurerm": [
                {
                    "features": [
                        {}
                    ]
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureInstance(object):
    azurerm_linux_virtual_machine = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.azurerm_linux_virtual_machine.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AdminSSHKey(object):
    admin_ssh_key = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, public_key: str, user: str):
        return cls(
            [
                {
                    "public_key": f"${{file(var.{public_key})}}",
                    "username": f"${{var.{user}}}"
                }
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['admin_ssh_key']


@attr.s
class NetworkInterface(object):
    network_interface_ids = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, name: str):
        return cls(
            [
                f"${{azurerm_network_interface.{name}[each.key].id}}"
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['network_interface_ids']


@attr.s
class OSDisk(object):
    os_disk = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, size: str, vol_type: str):
        return cls(
            [
                {
                    "caching": "ReadWrite",
                    "disk_size_gb": f"${{each.value.{size}}}",
                    "storage_account_type": f"${{each.value.{vol_type}}}"
                }
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['os_disk']


@attr.s
class NodeConfiguration(object):
    admin_ssh_key = attr.ib(validator=io(list))
    admin_username = attr.ib(validator=io(str))
    for_each = attr.ib(validator=io(str))
    location = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    network_interface_ids = attr.ib(validator=io(list))
    os_disk = attr.ib(validator=io(list))
    provisioner = attr.ib(validator=io(dict))
    resource_group_name = attr.ib(validator=io(str))
    size = attr.ib(validator=io(str))
    source_image_id = attr.ib(validator=io(str))
    zone = attr.ib(validator=io(str))

    @classmethod
    def construct(cls,
                  image: str,
                  root_size: str,
                  root_type: str,
                  for_each: str,
                  machine_type: str,
                  user: str,
                  public_key: str,
                  location: str,
                  resource_group: str,
                  provisioner: dict,
                  nic_name: str,
                  zone: str):
        return cls(
            AdminSSHKey.construct(public_key, user).as_dict,
            f"${{var.{user}}}",
            f"${{var.{for_each}}}",
            f"${{var.{location}}}",
            "${each.key}",
            NetworkInterface.construct(nic_name).as_dict,
            OSDisk.construct(root_size, root_type).as_dict,
            provisioner,
            f"${{var.{resource_group}}}",
            f"${{each.value.{machine_type}}}",
            f"${{var.{image}}}",
            f"${{each.value.{zone}}}",
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureManagedDisk(object):
    azurerm_managed_disk = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.azurerm_managed_disk.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class DiskConfiguration(object):
    create_option = attr.ib(validator=io(str))
    disk_size_gb = attr.ib(validator=io(str))
    for_each = attr.ib(validator=io(str))
    location = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    resource_group_name = attr.ib(validator=io(str))
    storage_account_type = attr.ib(validator=io(str))
    zone = attr.ib(validator=io(str))

    @classmethod
    def construct(cls,
                  disk_size: str,
                  for_each: str,
                  location: str,
                  resource_group: str,
                  disk_type: str,
                  zone: str):
        return cls(
            f"Empty",
            f"${{each.value.{disk_size}}}",
            f"${{var.{for_each}}}",
            f"${{var.{location}}}",
            "${each.key}-swap",
            f"${{var.{resource_group}}}",
            f"${{each.value.{disk_type}}}",
            f"${{each.value.{zone}}}",
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureNetworkInterface(object):
    azurerm_network_interface = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.azurerm_network_interface.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class IPConfiguration(object):
    ip_configuration = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, public_ip: str, subnet: str):
        return cls(
            [
                {
                    "name": "internal",
                    "private_ip_address_allocation": "Dynamic",
                    "public_ip_address_id": f"${{var.use_public_ip ? azurerm_public_ip.{public_ip}[each.key].id : null}}",
                    "subnet_id": f"${{data.azurerm_subnet.{subnet}[each.key].id}}"
                }
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['ip_configuration']


@attr.s
class NICConfiguration(object):
    for_each = attr.ib(validator=io(str))
    ip_configuration = attr.ib(validator=io(list))
    location = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    resource_group_name = attr.ib(validator=io(str))

    @classmethod
    def construct(cls,
                  for_each: str,
                  public_ip: str,
                  subnet: str,
                  location: str,
                  resource_group: str):
        return cls(
            f"${{var.{for_each}}}",
            IPConfiguration.construct(public_ip, subnet).as_dict,
            f"${{var.{location}}}",
            "${each.key}-nic",
            f"${{var.{resource_group}}}",
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureNetworkInterfaceNSG(object):
    azurerm_network_interface_security_group_association = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.azurerm_network_interface_security_group_association.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NICNSGConfiguration(object):
    for_each = attr.ib(validator=io(str))
    network_interface_id = attr.ib(validator=io(str))
    network_security_group_id = attr.ib(validator=io(str))

    @classmethod
    def construct(cls,
                  for_each: str,
                  nic_name: str,
                  nsg: str):
        return cls(
            f"${{var.{for_each}}}",
            f"${{azurerm_network_interface.{nic_name}[each.key].id}}",
            f"${{data.azurerm_network_security_group.{nsg}.id}}",
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzurePublicIP(object):
    azurerm_public_ip = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.azurerm_public_ip.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class PublicIPConfiguration(object):
    allocation_method = attr.ib(validator=io(str))
    for_each = attr.ib(validator=io(str))
    location = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    resource_group_name = attr.ib(validator=io(str))
    sku = attr.ib(validator=io(str))
    zones = attr.ib(validator=io(list))

    @classmethod
    def construct(cls,
                  for_each: str,
                  use_public_ip: str,
                  location: str,
                  resource_group: str,
                  zone: str):
        return cls(
            "Static",
            f"${{{{for k, v in var.{for_each} : k => v if var.{use_public_ip}}}}}",
            f"${{var.{location}}}",
            "${each.key}-pub",
            f"${{var.{resource_group}}}",
            "Standard",
            [
                f"${{each.value.{zone}}}"
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureDiskAttachment(object):
    azurerm_virtual_machine_data_disk_attachment = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.azurerm_virtual_machine_data_disk_attachment.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AttachedDiskConfiguration(object):
    caching = attr.ib(validator=io(str))
    for_each = attr.ib(validator=io(str))
    lun = attr.ib(validator=io(str))
    managed_disk_id = attr.ib(validator=io(str))
    virtual_machine_id = attr.ib(validator=io(str))

    @classmethod
    def construct(cls,
                  for_each: str,
                  disk_name: str,
                  node_name: str):
        return cls(
            "ReadWrite",
            f"${{var.{for_each}}}",
            "0",
            f"${{azurerm_managed_disk.{disk_name}[each.key].id}}",
            f"${{azurerm_linux_virtual_machine.{node_name}[each.key].id}}",
        )

    @property
    def as_dict(self):
        return self.__dict__
