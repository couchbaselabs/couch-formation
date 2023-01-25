##
##

import attr
from attr.validators import instance_of as io


@attr.s
class CapellaProviderBlock(object):
    provider = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls):
        return cls(
            {"couchbasecapella": [
                {}
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


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
class CapellaTerraformProvider(object):
    couchbasecapella = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, source: str, version: str):
        return cls(
            {
                "source": source,
                "version": version
            }
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CapellaCluster(object):
    couchbasecapella_hosted_cluster = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.couchbasecapella_hosted_cluster.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CapellaHostedCluster(object):
    hosted = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, cidr: str, provider: str, region: str):
        self.hosted.append(
            {
                "cidr": cidr,
                "provider": provider,
                "region": region
            }
        )
        return self

    @property
    def as_dict(self):
        return self.__dict__['hosted']


@attr.s
class CapellaClusterPlace(object):
    place = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, hosted: list, single_az: bool):
        self.place.append(
            {
                "hosted": hosted,
                "single_az": single_az
            }
        )
        return self

    @property
    def as_dict(self):
        return self.__dict__['place']


@attr.s
class CapellaServices(object):
    services = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, service: str):
        self.services.append(
            service
        )
        return self

    @property
    def as_dict(self):
        return self.__dict__['services']


@attr.s
class CapellaAWSStorage(object):
    storage = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, iops: str, size: str, disk_type: str):
        self.storage.append(
            {
                "iops": iops,
                "storage_size": size,
                "storage_type": disk_type
            }
        )
        return self

    @property
    def as_dict(self):
        return self.__dict__['storage']


@attr.s
class CapellaGCPStorage(object):
    storage = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, size: str, disk_type: str):
        self.storage.append(
            {
                "storage_size": size,
                "storage_type": disk_type
            }
        )
        return self

    @property
    def as_dict(self):
        return self.__dict__['storage']


@attr.s
class CapellaServerSpec(object):
    servers = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, compute: str, services: list, size: str, storage: list):
        self.servers.append(
            {
                "compute": compute,
                "services": services,
                "size": size,
                "storage": storage
            }
        )
        return self

    @property
    def as_dict(self):
        return self.__dict__['servers']


@attr.s
class CapellaSupportPackage(object):
    support_package = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, package: str):
        self.support_package.append(
            {
                "support_package_type": package,
                "timezone": "GMT"
            }
        )
        return self

    @property
    def as_dict(self):
        return self.__dict__['support_package']


@attr.s
class NodeConfiguration(object):
    name = attr.ib(validator=io(str))
    place = attr.ib(validator=io(list))
    project_id = attr.ib(validator=io(str))
    servers = attr.ib(validator=io(list))
    support_package = attr.ib(validator=io(list))
    timeouts = attr.ib(validator=io(list))

    @classmethod
    def construct(cls,
                  name: str,
                  place: list,
                  project_id: str,
                  servers: list,
                  support_package: list):
        return cls(
            name,
            place,
            project_id,
            servers,
            support_package,
            CapellaResourceTimeout.build().add().as_dict
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CapellaProject(object):
    couchbasecapella_project = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, resource_name: str, project_name: str):
        return cls(
            {
                resource_name: [
                    {
                        "name": project_name
                    }
                ]
            }
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CapellaResourceTimeout(object):
    timeouts = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self):
        self.timeouts.append(
            {
                "create": "15m",
                "delete": "15m",
                "update": "15m"
            }
        )
        return self

    @property
    def as_dict(self):
        return self.__dict__['timeouts']
