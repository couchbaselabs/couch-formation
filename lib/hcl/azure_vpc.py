##

import attr
from attr.validators import instance_of as io


@attr.s
class AzureProvider(object):
    provider = attr.ib(validator=io(dict))

    @classmethod
    def for_region(cls):
        entry = {
            "features": [{}]
        }
        return cls(
            {"azurerm": [entry]},
            )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Resources(object):
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
class Variable(object):
    variable = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, value: str, description: str, v_type: str):
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
class VPCConfig(object):
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
class RGElements(object):
    location = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, region_var: str, name: str):
        return cls(
            f"${{var.{region_var}}}",
            f"${{var.{name}}}-rg"
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class ResourceGroup(object):
    cf_rg = attr.ib(validator=io(list))

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
class RGResource(object):
    azurerm_resource_group = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, region_var: str, name: str):
        return cls(
            ResourceGroup.construct(RGElements.construct(region_var, name).as_dict).as_dict
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VNetEntry(object):
    cf_vpc = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, cidr_var: str, rg_name: str, env_name: str, subnet_var: str, nsg_name: str):
        return cls(
            [
               VNetElements.construct(cidr_var, rg_name, env_name, subnet_var, nsg_name).as_dict
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Subnet(object):
    id = attr.ib(validator=io(type(None)))
    address_prefix = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    security_group = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, subnet_var: str, env_name: str, nsg_name: str):
        return cls(
            None,
            f"${{var.{subnet_var}}}",
            f"${{var.{env_name}}}-subnet-1",
            f"${{azurerm_network_security_group.{nsg_name}.id}}"
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VNetElements(object):
    address_space = attr.ib(validator=io(list))
    location = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    resource_group_name = attr.ib(validator=io(str))
    subnet = attr.ib(validator=io(list))
    tags = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, cidr_var: str, rg_name: str, env_name: str, subnet_var: str, nsg_name: str):
        return cls(
            [f"${{var.{cidr_var}}}"],
            f"${{azurerm_resource_group.{rg_name}.location}}",
            f"${{var.{env_name}}}-vpc",
            f"${{azurerm_resource_group.{rg_name}.name}}",
            [Subnet.construct(subnet_var, env_name, nsg_name).as_dict],
            {"environment": f"${{var.{env_name}}}", "name": f"${{var.{env_name}}}-vpc"}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VNetResource(object):
    azurerm_virtual_network = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, cidr_var: str, rg_name: str, env_name: str, subnet_var: str, nsg_name: str):
        return cls(
            VNetEntry.construct(cidr_var, rg_name, env_name, subnet_var, nsg_name).as_dict
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NSGEntry(object):
    cf_nsg = attr.ib(validator=io(list))

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
class SecurityRule(object):
    entry = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, port_list: list, priority: int, src: str = "*", dst: str = "*", protocol: str = "Tcp"):
        return cls(
            {
                "description": "Cloud Formation Managed",
                "access": "Allow",
                "destination_address_prefix": dst,
                "destination_port_ranges": port_list,
                "direction": "Inbound",
                "name": name,
                "priority": priority,
                "protocol": protocol,
                "source_address_prefix": src,
                "source_port_range": "*",
                "destination_application_security_group_ids": None,
                "source_application_security_group_ids": None,
                "destination_address_prefixes": None,
                "destination_port_range": None,
                "source_address_prefixes": None,
                "source_port_ranges": None
            }
        )

    @property
    def as_dict(self):
        return self.__dict__['entry']


@attr.s
class NSGElements(object):
    location = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    resource_group_name = attr.ib(validator=io(str))
    security_rule = attr.ib(validator=io(list))
    tags = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, rg_name: str, env_name: str):
        return cls(
            f"${{azurerm_resource_group.{rg_name}.location}}",
            f"${{var.{env_name}}}-nsg",
            f"${{azurerm_resource_group.{rg_name}.name}}",
            [],
            {"environment": f"${{var.{env_name}}}", "name": f"${{var.{env_name}}}-nsg"}
        )

    def add(self, name: str, port_list: list, priority: int, src: str = "*", dst: str = "*", protocol: str = "Tcp"):
        security_rule = SecurityRule.construct(name, port_list, priority, src, dst, protocol).as_dict
        self.security_rule.append(security_rule)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NSGResource(object):
    azurerm_network_security_group = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, entry: dict):
        return cls(
            entry
        )

    @property
    def as_dict(self):
        return self.__dict__
