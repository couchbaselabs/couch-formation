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
class AWSTerraformProvider(object):
    aws = attr.ib(validator=io(dict))

    @classmethod
    def construct(cls, source: str):
        return cls(
            {"source": source}
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AWSInstance(object):
    aws_instance = attr.ib(validator=io(dict))

    @classmethod
    def build(cls):
        return cls(
            {}
        )

    def add(self, resource: dict):
        self.aws_instance.update(resource)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class BlockDevice(object):
    elements = attr.ib(validator=io(list))

    @classmethod
    def build(cls):
        return cls(
            []
        )

    def add(self, element: dict):
        self.elements.append(element)
        return self

    @property
    def as_dict(self):
        response = self.__dict__['elements']
        return response


@attr.s
class EbsElements(object):
    device_name = attr.ib(validator=io(str))
    iops = attr.ib(validator=io(str))
    volume_size = attr.ib(validator=io(str))
    volume_type = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, device: str, iops: str, size: str, vol_type: str):
        return cls(
            device,
            f"${{each.value.{iops}}}",
            f"${{each.value.{size}}}",
            f"${{each.value.{vol_type}}}"
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class RootElements(object):
    iops = attr.ib(validator=io(str))
    volume_size = attr.ib(validator=io(str))
    volume_type = attr.ib(validator=io(str))

    @classmethod
    def construct(cls, iops: str, size: str, vol_type: str):
        return cls(
            f"${{each.value.{iops}}}",
            f"${{each.value.{size}}}",
            f"${{each.value.{vol_type}}}"
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NodeConfiguration(object):
    ami = attr.ib(validator=io(str))
    availability_zone = attr.ib(validator=io(str))
    for_each = attr.ib(validator=io(str))
    instance_type = attr.ib(validator=io(str))
    key_name = attr.ib(validator=io(str))
    provisioner = attr.ib(validator=io(dict))
    root_block_device = attr.ib(validator=io(list))
    subnet_id = attr.ib(validator=io(str))
    vpc_security_group_ids = attr.ib(validator=io(str))
    tags = attr.ib(validator=io(dict))
    ebs_block_device = attr.ib(validator=attr.validators.optional(io(list)), default=None)

    @classmethod
    def construct(cls,
                  env_name: str,
                  ami_id: str,
                  zone: str,
                  for_each: str,
                  machine_type: str,
                  key_pair: str,
                  provisioner: dict,
                  root: dict,
                  subnet: str,
                  s_groups: str,
                  services: str,
                  swap_disk: Union[list, None] = None):
        return cls(
            f"${{var.{ami_id}}}",
            f"${{each.value.{zone}}}",
            f"${{var.{for_each}}}",
            f"${{each.value.{machine_type}}}",
            f"${{var.{key_pair}}}",
            provisioner,
            [root],
            f"${{each.value.{subnet}}}",
            f"${{var.{s_groups}}}",
            {
                "Environment": f"${{var.{env_name}}}",
                "Name": "${each.key}",
                "Services": f"${{each.value.{services}}}"
            },
            swap_disk
        )

    @property
    def as_dict(self):
        return self.__dict__
