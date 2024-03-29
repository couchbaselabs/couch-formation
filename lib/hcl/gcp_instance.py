##
##

import attr
from typing import Union
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
class GCPTerraformProvider(object):
    google = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, source: str):
        return cls(
            {"source": source}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class GCPInstance(object):
    google_compute_instance = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.google_compute_instance.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AttachedDisk(object):
    attached_disk = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, name: str):
        self.attached_disk.append({"source": f"${{google_compute_disk.{name}[each.key].self_link}}"})
        return self

    @property
    def as_dict(self):
        return self.__dict__['attached_disk']


@attr.s
class BootDisk(object):
    boot_disk = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, params: dict):
        return cls(
            [
                params
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['boot_disk']


@attr.s
class InitParams(object):
    initialize_params = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, image: str, size: str, vol_type: str):
        return cls(
           [
               {
                   "image": f"${{data.google_compute_image.{image}.self_link}}",
                   "size": f"${{each.value.{size}}}",
                   "type": f"${{each.value.{vol_type}}}"
               }
           ]
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Metadata(object):
    metadata = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, user: str, public_key: str):
        return cls(
            {
                "ssh-keys": f"${{var.{user}}}:${{file(var.{public_key})}}"
            }
        )

    @property
    def as_dict(self):
        return self.__dict__['metadata']


@attr.s
class NetworkInterface(object):
    network_interface = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, subnet: str, project: str):
        return cls(
            [
                {
                    "dynamic": {
                        "access_config": [
                            {
                                "content": [
                                    {}
                                ],
                                "for_each": "${var.use_public_ip ? [\"pub-ip\"] : []}"
                            }
                        ]
                    },
                    "subnetwork": f"${{each.value.{subnet}}}",
                    "subnetwork_project": f"${{var.{project}}}"
                }
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['network_interface']


@attr.s
class ServiceAccount(object):
    service_account = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, email: str):
        return cls(
            [
                {
                    "email": f"${{var.{email}}}",
                    "scopes": [
                        "cloud-platform"
                    ]
                }
            ]
        )

    @property
    def as_dict(self):
        return self.__dict__['service_account']


@attr.s
class ImageData(object):
    google_compute_image = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, image: str, project: str):
        return cls(
            {f"{name}": [
                {
                    "name": f"${{var.{image}}}",
                    "project": f"${{var.{project}}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class GCPProviderBlock(object):
    provider = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, account_file: str, project: str, region: str):
        return cls(
            {"google": [
                {
                    "credentials": f"${{file(var.{account_file})}}",
                    "project": f"${{var.{project}}}",
                    "region": f"${{var.{region}}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class GCPDisk(object):
    google_compute_disk = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, name: str, for_each: str, project: str, size: str, vol_type: str, zone: str):
        return cls(
            {f"{name}": [
                {
                    "for_each": f"${{var.{for_each}}}",
                    "name": "${each.key}-disk",
                    "project": f"${{var.{project}}}",
                    "size": f"${{each.value.{size}}}",
                    "type": f"${{each.value.{vol_type}}}",
                    "zone": f"${{each.value.{zone}}}"
                }
            ]}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NodeConfiguration(object):
    boot_disk = attr.ib(validator=io(list))
    for_each = attr.ib(validator=io(str))
    machine_type = attr.ib(validator=io(str))
    metadata = attr.ib(validator=io(dict))
    name = attr.ib(validator=io(str))
    network_interface = attr.ib(validator=io(list))
    project = attr.ib(validator=io(str))
    service_account = attr.ib(validator=io(list))
    zone = attr.ib(validator=io(str))
    provisioner = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    attached_disk = attr.ib(validator=attr.validators.optional(io(dict)), default=None)

    @classmethod
    def construct(cls,
                  image: str,
                  root_size: str,
                  root_type: str,
                  for_each: str,
                  machine_type: str,
                  user: str,
                  public_key: str,
                  subnet: str,
                  project: str,
                  email: str,
                  zone: str,
                  provisioner: Union[dict, None] = None,
                  attached_disk: Union[dict, None] = None):
        return cls(
            BootDisk.construct(InitParams.construct(image, root_size, root_type).as_dict).as_dict,
            f"${{var.{for_each}}}",
            f"${{each.value.{machine_type}}}",
            Metadata.construct(user, public_key).as_dict,
            "${each.key}",
            NetworkInterface.construct(subnet, project).as_dict,
            f"${{var.{project}}}",
            ServiceAccount.construct(email).as_dict,
            f"${{each.value.{zone}}}",
            provisioner,
            attached_disk
        )

    @property
    def as_dict(self):
        block = {k: v for k, v in self.__dict__.items() if v is not None}
        return block
