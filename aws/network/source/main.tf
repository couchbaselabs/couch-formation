##

variable "region_name" {
  description = "Region name"
  default     = "us-east-2"
  type        = string
}

variable "cf_env_name" {
  description = "Couchbase cluster name"
  default     = "dev10db"
  type        = string
}

variable "cf_vpc_cidr" {
  description = "Couchbase cluster name"
  default     = "10.11.0.0/16"
  type        = string
}

variable "cf_subnet_cidr_1" {
  description = "Couchbase cluster name"
  default     = "10.11.1.0/24"
  type        = string
}

variable "cf_subnet_cidr_2" {
  description = "Couchbase cluster name"
  default     = "10.11.2.0/24"
  type        = string
}

variable "cf_subnet_cidr_3" {
  description = "Couchbase cluster name"
  default     = "10.11.3.0/24"
  type        = string
}

variable "cf_subnet_az_1" {
  description = "Couchbase cluster name"
  default     = "us-east-2a"
  type        = string
}

variable "cf_subnet_az_2" {
  description = "Couchbase cluster name"
  default     = "us-east-2b"
  type        = string
}

variable "cf_subnet_az_3" {
  description = "Couchbase cluster name"
  default     = "us-east-2c"
  type        = string
}

provider "aws" {
  region = var.region_name
}

resource "aws_vpc" "cf_vpc" {
  cidr_block = var.cf_vpc_cidr

  tags = {
    Name = "${var.cf_env_name}-vpc"
    Environment = var.cf_env_name
  }
}

resource "aws_internet_gateway" "cf_gw" {
  vpc_id = aws_vpc.cf_vpc.id

  tags = {
    Name = "${var.cf_env_name}-gw"
    Environment = var.cf_env_name
  }
}

resource "aws_route_table" "cf_rt" {
  vpc_id = aws_vpc.cf_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.cf_gw.id
  }

  tags = {
    Name = "${var.cf_env_name}-rt"
    Environment = var.cf_env_name
  }
}

resource "aws_subnet" "cf_subnet_1" {
  vpc_id     = aws_vpc.cf_vpc.id
  cidr_block = var.cf_subnet_cidr_1
  availability_zone = var.cf_subnet_az_1
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cf_env_name}-subnet-1"
    Environment = var.cf_env_name
  }
}

resource "aws_route_table_association" "cf_subnet_1" {
  subnet_id      = aws_subnet.cf_subnet_1.id
  route_table_id = aws_route_table.cf_rt.id
}

resource "aws_subnet" "cf_subnet_2" {
  vpc_id     = aws_vpc.cf_vpc.id
  cidr_block = var.cf_subnet_cidr_2
  availability_zone = var.cf_subnet_az_2
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cf_env_name}-subnet-2"
    Environment = var.cf_env_name
  }
}

resource "aws_route_table_association" "cf_subnet_2" {
  subnet_id      = aws_subnet.cf_subnet_2.id
  route_table_id = aws_route_table.cf_rt.id
}

resource "aws_subnet" "cf_subnet_3" {
  vpc_id     = aws_vpc.cf_vpc.id
  cidr_block = var.cf_subnet_cidr_3
  availability_zone = var.cf_subnet_az_3
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cf_env_name}-subnet-3"
    Environment = var.cf_env_name
  }
}

resource "aws_route_table_association" "cf_subnet_3" {
  subnet_id      = aws_subnet.cf_subnet_3.id
  route_table_id = aws_route_table.cf_rt.id
}

resource "aws_security_group" "cf_sg" {
  name        = "allow_tls"
  description = "Allow TLS inbound traffic"
  vpc_id      = aws_vpc.cf_vpc.id
  depends_on = [aws_vpc.cf_vpc]

  ingress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = [aws_vpc.cf_vpc.cidr_block]
  }

  ingress {
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  ingress {
    from_port        = 8091
    to_port          = 8097
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  ingress {
    from_port        = 9123
    to_port          = 9123
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  ingress {
    from_port        = 9140
    to_port          = 9140
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  ingress {
    from_port        = 11210
    to_port          = 11210
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  ingress {
    from_port        = 11280
    to_port          = 11280
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  ingress {
    from_port        = 11207
    to_port          = 11207
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  ingress {
    from_port        = 18091
    to_port          = 18097
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "${var.cf_env_name}-sg"
    Environment = var.cf_env_name
  }
}
