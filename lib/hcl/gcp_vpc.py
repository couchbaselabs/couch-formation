##

import attr
from attr.validators import instance_of as io


@attr.s
class GCPProvider(object):
    provider = attr.ib(validator=io(dict))

    @classmethod
    def for_region(cls, account_var: str, project_var: str, region_var: str):
        entry = {
            "credentials": f"${{file(var.{account_var})}}",
            "project": f"${{var.{project_var}}}",
            "region": f"${{var.{region_var}}}"
        }
        return cls(
            {"google": [entry]},
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
class NetworkElements(object):
    auto_create_subnetworks = attr.ib(validator=io(bool))
    name = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, auto_create: bool, name: str):
        return cls(
            auto_create,
            f"${{var.{name}}}-vpc"
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Network(object):
    cf_vpc = attr.ib(validator=io(list))

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
class NetworkResource(object):
    google_compute_network = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, auto_create: bool, name: str):
        return cls(
            Network.construct(NetworkElements.construct(auto_create, name).as_dict).as_dict
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class SubnetElements(object):
    ip_cidr_range = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    network = attr.ib(validator=io(str))
    region = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, subnet_var: str, name: str, vpc_name: str, region: str):
        return cls(
            f"${{var.{subnet_var}}}",
            f"${{var.{name}}}-subnet",
            f"${{google_compute_network.{vpc_name}.id}}",
            f"${{var.{region}}}"
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Subnet(object):
    cf_subnet_1 = attr.ib(validator=io(list))

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
class SubnetResource(object):
    google_compute_subnetwork = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, subnet_var: str, name: str, vpc_name: str, region: str):
        return cls(
            Subnet.construct(SubnetElements.construct(subnet_var, name, vpc_name, region).as_dict).as_dict
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class FirewallEntry(object):
    rule = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, ports: list, protocol: str, env_name: str, vpc_name: str, cidr: list):
        return cls(
            {name: [
               FireElements.construct(name, ports, protocol, env_name, vpc_name, cidr).as_dict
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__['rule']


@attr.s
class DefaultFirewallEntry(object):
    rule = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, env_name: str, vpc_name: str, cidr_var: str):
        return cls(
            {"cf-fw-vpc": [
                {
                    "allow": [{"protocol": "all"}],
                    "name": f"${{var.{env_name}}}-cf-fw-vpc",
                    "network": f"${{google_compute_network.{vpc_name}.name}}",
                    "source_ranges": [f"${{var.{cidr_var}}}"]
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__['rule']


@attr.s
class AllowList(object):
    ports = attr.ib(validator=io(list))
    protocol = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, ports: list, protocol: str):
        return cls(
            ports,
            protocol
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class FireElements(object):
    allow = attr.ib(validator=io(list))
    name = attr.ib(validator=io(str))
    network = attr.ib(validator=io(str))
    source_ranges = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, r_name: str, ports: list, protocol: str, env_name: str, vpc_name: str, cidr: list):
        return cls(
            [AllowList.construct(ports, protocol).as_dict],
            f"${{var.{env_name}}}-{r_name}",
            f"${{google_compute_network.{vpc_name}.name}}",
            cidr
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class FirewallResource(object):
    google_compute_firewall = attr.ib(validator=io(dict))

    @classmethod
    def build(cls, env_name: str, vpc_name: str, cidr_var: str):
        return cls(
            DefaultFirewallEntry.construct(env_name, vpc_name, cidr_var).as_dict
        )

    def add(self, name: str, ports: list, protocol: str, env_name: str, vpc_name: str, cidr: list):
        firewall_item = FirewallEntry.construct(name, ports, protocol, env_name, vpc_name, cidr).as_dict
        self.google_compute_firewall.update(firewall_item)
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
