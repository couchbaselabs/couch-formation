##
##

# Cloud Base Config

AWS_CONFIG = """CREATE TABLE IF NOT EXISTS aws_config(
              record_id INTEGER PRIMARY KEY,
              sso_url TEXT,
              sso_region TEXT,
              account TEXT,
              region TEXT,
              access_key TEXT,
              secret_key TEXT,
              session_token TEXT)
"""

GCP_CONFIG = """CREATE TABLE IF NOT EXISTS gcp_config(
              record_id INTEGER PRIMARY KEY,
              account_file TEXT,
              default_region TEXT,
              project_id TEXT)
"""

AZURE_CONFIG = """CREATE TABLE IF NOT EXISTS azure_config(
              record_id INTEGER PRIMARY KEY,
              default_region TEXT,
              subscription_id TEXT,
              resource_group TEXT)
"""

VMWARE_CONFIG = """CREATE TABLE IF NOT EXISTS vmware_config(
              record_id INTEGER PRIMARY KEY,
              hostname TEXT,
              username TEXT,
              password TEXT,
              datacenter TEXT)
"""

CAPELLA_CONFIG = """CREATE TABLE IF NOT EXISTS capella_config(
              record_id INTEGER PRIMARY KEY,
              access_key TEXT,
              secret_key TEXT)
"""

# Cloud Data

AWS_REGIONS = """CREATE TABLE IF NOT EXISTS aws_regions(
                 record_id INTEGER PRIMARY KEY,
                 name TEXT,
                 zones TEXT)
"""

GCP_REGIONS = """CREATE TABLE IF NOT EXISTS gcp_regions(
                 record_id INTEGER PRIMARY KEY,
                 name TEXT,
                 zones TEXT)
"""

AZURE_REGIONS = """CREATE TABLE IF NOT EXISTS azure_regions(
                 record_id INTEGER PRIMARY KEY,
                 name TEXT,
                 zones TEXT)
"""

SSH_PUBLIC_KEY = """CREATE TABLE IF NOT EXISTS ssh_public_keys(
                    key_id INTEGER PRIMARY KEY,
                    file_path TEXT,
                    key_encoded TEXT,
                    fingerprint TEXT,
                    description TEXT)
"""

SSH_PRIVATE_KEY = """CREATE TABLE IF NOT EXISTS ssh_private_keys(
                     key_id INTEGER PRIMARY KEY,
                     file_path TEXT,
                     key_encoded TEXT
                     fingerprint TEXT)
"""

SSH_DATA_TABLE = """CREATE TABLE IF NOT EXISTS ssh_key(
                    record_id INTEGER PRIMARY KEY,
                    key_name TEXT,
                    aws_key_pair TEXT,
                    public_key INTEGER,
                    private_key INTEGER)
"""

SHELL_USER = """CREATE TABLE IF NOT EXISTS shell_user(
                record_id INTEGER PRIMARY KEY,
                user_name TEXT,
                ssh_key INTEGER)
"""

AWS_VPC = """CREATE TABLE IF NOT EXISTS aws_vpc(
             record_id INTEGER PRIMARY KEY,
             region INTEGER,
             vpc_id TEXT,
             subnet_list TEXT,
             security_group TEXT,
             use_public_ip NUMERIC)
"""
