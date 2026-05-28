# Networking — baseline is intentionally locked down.
# SSH/RDP are restricted to an internal CIDR (RFC1918), satisfying CIS 4.1/4.2.

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "terraguard-demo-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "private" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = false

  tags = {
    Name = "terraguard-demo-private"
  }
}

resource "aws_security_group" "app" {
  name        = "terraguard-app-sg"
  description = "Application security group — internal ingress only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH from internal management subnet only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  ingress {
    description = "HTTPS from internal VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "terraguard-app-sg"
  }
}
