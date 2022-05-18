##
##

import logging
from Crypto.PublicKey import RSA
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import hashlib
from lib.varfile import varfile
from lib.ask import ask
from lib.exceptions import *
from lib.prereq import prereq


class ssh(object):
    VARIABLES = [
        ('SSH_PUBLIC_KEY', 'ssh_public_key', 'get_public_key', None),
        ('SSH_PRIVATE_KEY', 'ssh_private_key', 'get_private_key', None),
        ('SSH_PUBLIC_KEY_FILE', 'ssh_public_key_file', 'get_ssh_public_key_file', None),
    ]
    PREREQUISITES = {
        'get_public_key': [
            'get_private_key'
        ]
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()
        self.ssh_public_key = None
        self.ssh_key_fingerprint = None
        self.ssh_private_key = None
        self.ssh_public_key_file = None

    def set_key_fingerprint(self, fingerprint: str):
        self.ssh_key_fingerprint = fingerprint

    @prereq(PREREQUISITES)
    def get_public_key(self) -> str:
        fh = open(self.ssh_private_key, 'r')
        key_pem = fh.read()
        fh.close()
        rsa_key = RSA.importKey(key_pem)
        modulus = rsa_key.n
        pubExpE = rsa_key.e
        priExpD = rsa_key.d
        primeP = rsa_key.p
        primeQ = rsa_key.q
        private_key = RSA.construct((modulus, pubExpE, priExpD, primeP, primeQ))
        public_key = private_key.public_key().exportKey('OpenSSH')
        self.ssh_public_key = public_key.decode('utf-8')
        return self.ssh_public_key

    def get_private_key(self, default=None, write=None) -> str:
        """Get path to SSH private key PEM file"""
        inquire = ask()
        dir_list = []
        key_file_list = []
        key_directory = os.environ['HOME'] + '/.ssh'

        if write:
            self.ssh_private_key = write
            return self.ssh_private_key

        if self.ssh_private_key:
            return self.ssh_private_key

        for file_name in os.listdir(key_directory):
            full_path = key_directory + '/' + file_name
            dir_list.append(full_path)

        for i in range(len(dir_list)):
            file_handle = open(dir_list[i], 'r')
            blob = file_handle.read()
            pem_key_bytes = str.encode(blob)

            try:
                key = serialization.load_pem_private_key(
                    pem_key_bytes, password=None, backend=default_backend()
                )
            except Exception:
                continue

            self.logger.info("Found private key %s" % dir_list[i])
            key_file_list.append(dir_list[i])
            pri_der = key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            der_digest = hashlib.sha1(pri_der)
            hex_digest = der_digest.hexdigest()
            key_fingerprint = ':'.join(hex_digest[i:i + 2] for i in range(0, len(hex_digest), 2))
            if key_fingerprint == self.ssh_key_fingerprint:
                print("Auto selecting SSH private key %s" % dir_list[i])
                self.ssh_private_key = dir_list[i]
                return self.ssh_private_key

        selection = inquire.ask_list('Select SSH private key', key_file_list, default=default)
        self.ssh_private_key = key_file_list[selection]
        return self.ssh_private_key

    def generate_public_key_file(self, public_file: str) -> bool:
        """Write public key file"""
        public_key = self.get_public_key()
        try:
            file_handle = open(public_file, 'w')
            file_handle.write(public_key)
            file_handle.write("\n")
            file_handle.close()
            return True
        except OSError as err:
            raise SSHError(f"generate_public_key_file: can not write public key file: {err}.")

    def get_ssh_public_key_file(self, ssh_private_key=None, default=None, write=None) -> str:
        """Get SSH public key file"""
        inquire = ask()
        dir_list = []
        key_file_list = []
        key_directory = os.environ['HOME'] + '/.ssh'

        if write:
            self.ssh_public_key_file = write
            return self.ssh_public_key_file

        if self.ssh_public_key_file:
            return self.ssh_public_key_file

        if self.ssh_private_key:
            private_key_dir = os.path.dirname(self.ssh_private_key)
            private_key_file = os.path.basename(self.ssh_private_key)
            private_key_name = os.path.splitext(private_key_file)[0]
            check_file_name = private_key_dir + '/' + private_key_name + '.pub'
            if os.path.exists(check_file_name):
                print("Auto selecting public key file %s" % check_file_name)
                self.ssh_public_key_file = check_file_name
                return self.ssh_public_key_file
            else:
                if inquire.ask_yn("Generate public key from private key %s" % ssh_private_key):
                    if self.generate_public_key_file(check_file_name):
                        self.ssh_public_key_file = check_file_name
                        return self.ssh_public_key_file

        for file_name in os.listdir(key_directory):
            full_path = key_directory + '/' + file_name
            dir_list.append(full_path)

        for i in range(len(dir_list)):
            file_handle = open(dir_list[i], 'r')
            public_key = file_handle.readline()
            file_size = os.fstat(file_handle.fileno()).st_size
            read_size = len(public_key)
            if file_size != read_size:
                continue
            public_key = public_key.rstrip()
            key_parts = public_key.split(' ')
            pub_key_part = ' '.join(key_parts[0:2])
            pub_key_bytes = str.encode(pub_key_part)
            try:
                key = serialization.load_ssh_public_key(pub_key_bytes)
            except Exception:
                continue
            self.logger.info("Found public key %s" % dir_list[i])
            key_file_list.append(dir_list[i])

        selection = inquire.ask_list('Select SSH public key', key_file_list, default=default)
        self.ssh_public_key_file = key_file_list[selection]
        return self.ssh_public_key_file
