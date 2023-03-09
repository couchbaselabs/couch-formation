##
##

import attr
from attr.validators import instance_of as io


@attr.s
class ProviderResource(object):
    provider = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, element: dict):
        return cls(
            element
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VSphereProvider(object):
    vsphere = attr.ib(validator=io(list))

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
class VSphereSettings(object):
    vsphere = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, server: str, password: str):
        return cls(
            {
                "allow_unverified_ssl": True,
                "password": f"${{var.{password}}}",
                "user": "${var.vsphere_user}",
                "vsphere_server": f"${{var.{server}}}"
            }
        )

    @property
    def as_dict(self):
        return self.__dict__['vsphere']


@attr.s
class VMwareInstance(object):
    vsphere_virtual_machine = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.vsphere_virtual_machine.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class DatacenterData(object):
    vsphere_datacenter = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, datacenter: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{datacenter}}}",
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class DatastoreData(object):
    vsphere_datastore = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, datastore: str, dc_data: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{datastore}}}",
                    "datacenter_id": f"${{data.vsphere_datacenter.{dc_data}.id}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class DVSData(object):
    vsphere_distributed_virtual_switch = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, dvs_switch: str, dc_data: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{dvs_switch}}}",
                    "datacenter_id": f"${{data.vsphere_datacenter.{dc_data}.id}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NetworkData(object):
    vsphere_network = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, network: str, dc_data: str, dvs_data: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{network}}}",
                    "datacenter_id": f"${{data.vsphere_datacenter.{dc_data}.id}}",
                    "distributed_virtual_switch_uuid": f"${{data.vsphere_distributed_virtual_switch.{dvs_data}.id}}",
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class ResourcePoolData(object):
    vsphere_resource_pool = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, cluster: str, dc_data: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{cluster}}}/Resources",
                    "datacenter_id": f"${{data.vsphere_datacenter.{dc_data}.id}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VMData(object):
    vsphere_virtual_machine = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, vm_name_var: str, dc_data: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{vm_name_var}}}",
                    "datacenter_id": f"${{data.vsphere_datacenter.{dc_data}.id}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class HostData(object):
    vsphere_host = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, for_each: str, zone: str, dc_data: str):
        return cls(
            {f"host": [
                {
                    "for_each": f"${{var.{for_each}}}",
                    "name": f"${{each.value.{zone}}}",
                    "datacenter_id": f"${{data.vsphere_datacenter.{dc_data}.id}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VSphereFolder(object):
    vsphere_folder = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, vsphere_folder: str, dc_data: str):
        return cls(
            {f"{name}": [
                {
                    "datacenter_id": f"${{data.vsphere_datacenter.{dc_data}.id}}",
                    "path": f"${{var.{vsphere_folder}}}",
                    "type": "vm"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CloneConfiguration(object):
    clone = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, dns_server_list: str, dns_domain_list: str, node_gateway: str, domain_name: str, node_ip_address: str, node_netmask: str, template: str):
        return cls(
            [
                {
                    "customize": [
                        {
                            "dns_server_list": f"${{var.{dns_server_list}}}",
                            "dns_suffix_list": f"${{var.{dns_domain_list}}}",
                            "ipv4_gateway": f"${{each.value.{node_gateway}}}",
                            "linux_options": [
                                {
                                    "domain": f"${{var.{domain_name}}}",
                                    "host_name": "${each.key}"
                                }
                            ],
                            "network_interface": [
                                {
                                    "ipv4_address": f"${{each.value.{node_ip_address}}}",
                                    "ipv4_netmask": f"${{each.value.{node_netmask}}}"
                                }
                            ]
                        }
                    ],
                    "template_uuid": f"${{data.vsphere_virtual_machine.{template}.id}}"
                }
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['clone']


@attr.s
class DiskConfiguration(object):
    disk = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, template: str):
        return cls(
            [
                {
                    "label": "disk0",
                    "size": f"${{data.vsphere_virtual_machine.{template}.disks.0.size}}",
                    "thin_provisioned": f"${{data.vsphere_virtual_machine.{template}.disks.0.thin_provisioned}}"
                }
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['disk']


@attr.s
class NetworkConfiguration(object):
    network_interface = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, network: str):
        return cls(
            [
                {
                    "network_id": f"${{data.vsphere_network.{network}.id}}"
                }
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['network_interface']


@attr.s
class NodeConfiguration(object):
    clone = attr.ib(validator=io(list))
    datastore_id = attr.ib(validator=io(str))
    disk = attr.ib(validator=io(list))
    folder = attr.ib(validator=io(str))
    for_each = attr.ib(validator=io(str))
    guest_id = attr.ib(validator=io(str))
    memory = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    network_interface = attr.ib(validator=io(list))
    num_cpus = attr.ib(validator=io(str))
    provisioner = attr.ib(validator=io(dict))
    resource_pool_id = attr.ib(validator=io(str))
    host_system_id = attr.ib(validator=io(str))
    scsi_type = attr.ib(validator=io(str))

    @classmethod
    def construct(cls,
                  dns_server_list: str,
                  dns_domain_list: str,
                  node_gateway: str,
                  domain_name: str,
                  node_ip_address: str,
                  node_netmask: str,
                  template: str,
                  datastore: str,
                  folder: str,
                  cluster_spec: str,
                  vm_mem_size: str,
                  network: str,
                  vm_cpu_cores: str,
                  provisioner: dict,
                  pool: str):
        return cls(
            CloneConfiguration.construct(dns_server_list, dns_domain_list, node_gateway, domain_name, node_ip_address, node_netmask, template).as_dict,
            f"${{data.vsphere_datastore.{datastore}.id}}",
            DiskConfiguration.construct(template).as_dict,
            f"${{vsphere_folder.{folder}.path}}",
            f"${{var.{cluster_spec}}}",
            f"${{data.vsphere_virtual_machine.{template}.guest_id}}",
            f"${{var.{vm_mem_size}}}",
            "${each.key}",
            NetworkConfiguration.construct(network).as_dict,
            f"${{var.{vm_cpu_cores}}}",
            provisioner,
            f"${{data.vsphere_resource_pool.{pool}.id}}",
            f"${{data.vsphere_host.host[each.key].id}}",
            f"${{data.vsphere_virtual_machine.{template}.scsi_type}}",
        )

    @property
    def as_dict(self):
        return self.__dict__
