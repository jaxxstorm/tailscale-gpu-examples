locals {
  vpc_cidr           = "172.16.0.0/16"
  vpc_public_subnets = ["172.16.3.0/24", "172.16.4.0/24", "172.16.5.0/24"]
}

module "lbr-vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"

  name = "lbr-gpu-webinar"
  cidr = local.vpc_cidr

  azs            = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  public_subnets = local.vpc_public_subnets

}



module "ubuntu-tailscale-aws" {
  source         = "lbrlabs/tailscale/cloudinit"
  version        = "0.0.3"
  auth_key       = var.tailscale_auth_key
  enable_ssh     = true
  hostname       = "aws-gpu"
  advertise_tags = ["tag:gpu"]
  additional_parts = [{
    content = file("files/run-ollama.sh")
    content_type = "x-shellscript"
    filename = "run-ollama.sh"
  }]
}

resource "aws_security_group" "main" {
  vpc_id      = module.lbr-vpc.vpc_id
  description = "Tailscale required traffic"

  ingress {
    from_port   = 41641
    to_port     = 41641
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Tailscale UDP port"
  }

  # ingress {
  #   from_port   = 22
  #   to_port     = 22
  #   protocol    = "tcp"
  #   cidr_blocks = ["0.0.0.0/0"]
  #   description = "SSH port"
  # }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
}

resource "aws_key_pair" "main" {
  key_name   = "lbr-gpu"
  public_key = file("~/.ssh/id_rsa.pub")
}


resource "aws_instance" "web" {
  #checkov:skip=CKV2_AWS_41:Testing instance
  #checkov:skip=CKV_AWS_8:Testing instance
  #checkov:skip=CKV_AWS_126:Testing instance
  #checkov:skip=CKV_AWS_88:Testing instance
  ami             = "ami-06d9c478e32dd66af"
  instance_type   = "g4dn.xlarge"
  subnet_id       = module.lbr-vpc.public_subnets[0]
  security_groups = [aws_security_group.main.id]

  key_name = aws_key_pair.main.key_name


  ebs_optimized = true

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = 100
    volume_type = "gp3"
  }

  user_data_base64            = module.ubuntu-tailscale-aws.rendered
  associate_public_ip_address = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name = "lbr-aws-gpu"
  }
}

data "tailscale_device" "aws" {
  hostname = "aws-gpu"
  wait_for = "5m"
  depends_on = [ aws_instance.web ]
}

output "devices" {
    value = data.tailscale_device.aws.addresses
}
