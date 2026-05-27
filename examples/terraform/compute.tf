# Compute — EC2 with IMDSv2 required and encrypted EBS root volume.

resource "aws_instance" "app" {
  ami           = "ami-0abcdef1234567890"
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.private.id

  vpc_security_group_ids = [aws_security_group.app.id]

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 enforced (CIS 5.6)
    http_put_response_hop_limit = 1
  }

  root_block_device {
    encrypted   = true
    volume_type = "gp3"
    volume_size = 20
  }

  monitoring = true

  tags = {
    Name        = "terraguard-demo-app"
    Environment = var.environment
  }
}

resource "aws_ebs_volume" "data" {
  availability_zone = "us-east-1a"
  size              = 50
  encrypted         = true
  type              = "gp3"

  tags = {
    Name = "terraguard-demo-data"
  }
}
