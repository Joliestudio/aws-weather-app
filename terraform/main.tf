terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region = var.aws_region
}

# 1. 建立 Security Group (防火牆)
# 允許 Port 8501 (Streamlit) 和 SSH (22)
resource "aws_security_group" "weather_sg" {
  name        = "weather_app_sg"
  description = "Allow Streamlit traffic"

  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 2. 尋找最新的 Amazon Linux 2023 AMI (系統映像檔)
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

# 3. 建立 EC2 實體
resource "aws_instance" "app_server" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro" # 免費方案 Free Tier

  vpc_security_group_ids = [aws_security_group.weather_sg.id]

  # User Data: 開機時自動執行的腳本
  user_data = <<-EOF
              #!/bin/bash
              # 更新並安裝 Docker
              yum update -y
              yum install -y docker
              systemctl start docker
              systemctl enable docker
              usermod -a -G docker ec2-user

              # 下載並執行你的 Docker Image
              # 注意：這裡直接注入了你的 API Key 和 Image 名稱
              docker run -d -p 8501:8501 \
                -e OPENWEATHER_API_KEY="${var.weather_api_key}" \
                -e GOOGLE_API_KEY="${var.google_api_key}" \
                --restart always \
                ${var.docker_image}
              EOF

  # 為了讓 Terraform 知道如果 User Data 改了要重開機
  user_data_replace_on_change = true

  tags = {
    Name = "Weather-App-Terraform"
  }
}

# 4. 輸出結果 (顯示公網 IP)
output "public_ip" {
  description = "應用程式的公開 IP 位址"
  value       = aws_instance.app_server.public_ip
}

output "app_url" {
  description = "點擊此連結開啟氣象站"
  value       = "http://${aws_instance.app_server.public_ip}:8501"
}