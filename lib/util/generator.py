##
##

import random
import logging
import uuid


class Generator(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def random_number(value: int) -> int:
        bits = value.bit_length()
        while True:
            n = random.getrandbits(bits) % value
            if n <= value:
                break
        return n

    @staticmethod
    def random_string_lower(n: int) -> str:
        min_lc = ord(b'a')
        len_lc = 26
        ba = bytearray(random.getrandbits(8) for i in range(n))
        for i, b in enumerate(ba):
            ba[i] = min_lc + b % len_lc
        return ba.decode('utf-8')

    @staticmethod
    def random_string_upper(n: int) -> str:
        min_lc = ord(b'A')
        len_lc = 26
        ba = bytearray(random.getrandbits(8) for i in range(n))
        for i, b in enumerate(ba):
            ba[i] = min_lc + b % len_lc
        return ba.decode('utf-8')

    @staticmethod
    def random_hash(n: int) -> str:
        ba = bytearray(random.getrandbits(8) for i in range(n))
        for i, b in enumerate(ba):
            min_lc = ord(b'0') if b < 85 else ord(b'A') if b < 170 else ord(b'a')
            len_lc = 10 if b < 85 else 26
            ba[i] = min_lc + b % len_lc
        return ba.decode('utf-8')

    @staticmethod
    def get_uuid(name: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_OID, name))

    @staticmethod
    def get_host_id() -> str:
        return str(uuid.getnode())
