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

    def add(self, source: str):
        self.attached_disk.append({"source": source})
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
        return self.__dict__


@attr.s
class InitParams(object):
    initialize_params = attr.ib(validator=io(list))

    @classmethod
    def construct(cls, image: str, size: str, vol_type: str):
        return cls(
           [
               {
                   "image": f"${{data.google_compute_image.{image}.self_link}}",
                   "size": f"${{var.{size}}}",
                   "type": f"${{var.{vol_type}}}"
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
        return self.__dict__


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
        return self.__dict__


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
        return self.__dict__


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
class NodeConfiguration(object):
    boot_disk = attr.ib(validator=io(dict))
    for_each = attr.ib(validator=io(str))
    machine_type = attr.ib(validator=io(str))
    metadata = attr.ib(validator=io(dict))
    name = attr.ib(validator=io(str))
    network_interface = attr.ib(validator=io(dict))
    project = attr.ib(validator=io(str))
    provisioner = attr.ib(validator=io(dict))
    service_account = attr.ib(validator=io(dict))
    zone = attr.ib(validator=io(str))
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
                  provisioner: dict,
                  email: str,
                  zone: str,
                  attached_disk: Union[list, None] = None):
        return cls(
            BootDisk.construct(InitParams.construct(image, root_size, root_type).as_dict).as_dict,
            f"${{var.{for_each}}}",
            f"${{var.{machine_type}}}",
            Metadata.construct(user, public_key).as_dict,
            "${each.key}",
            NetworkInterface.construct(subnet, project).as_dict,
            f"${{var.{project}}}",
            provisioner,
            ServiceAccount.construct(email).as_dict,
            f"${{each.value.{zone}}}",
            attached_disk
        )

    @property
    def as_dict(self):
        return self.__dict__
