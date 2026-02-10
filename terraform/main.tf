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
              yum update -y
              yum install -y docker
              systemctl start docker
              systemctl enable docker
              usermod -a -G docker ec2-user

              # 這裡加入了 DB_HOST, DB_USER, DB_PASS
              docker run -d -p 8501:8501 \
                -e OPENWEATHER_API_KEY="${var.weather_api_key}" \
                -e GOOGLE_API_KEY="${var.google_api_key}" \
                -e DB_HOST="${aws_db_instance.default.address}" \
                -e DB_USER="${aws_db_instance.default.username}" \
                -e DB_PASS="${var.db_password}" \
                -e DB_NAME="${aws_db_instance.default.db_name}" \
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

# --- 1. 資料庫的 Security Group (只允許 EC2 連線) ---
resource "aws_security_group" "rds_sg" {
  name        = "weather_rds_sg"
  description = "Allow traffic from EC2 only"

  ingress {
    from_port       = 5432 # Postgres 預設 Port
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.weather_sg.id] # 關鍵：只允許來自 Web Server SG 的連線
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- 2. RDS 實體 (PostgreSQL) ---
resource "aws_db_instance" "default" {
  allocated_storage    = 20
  db_name              = "weatherdb"
  engine               = "postgres"
  engine_version       = "16.3" # 使用較新的穩定版
  instance_class       = "db.t3.micro" # Free Tier 適用
  username             = "dbadmin"
  password             = var.db_password
  parameter_group_name = "default.postgres16"
  skip_final_snapshot  = true # 測試用，刪除時不備份 (省錢)
  publicly_accessible  = false # 安全！不開放公網連線
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
}

# --- 3. 修正 EC2 User Data (注入 DB 連線資訊) ---
# 請找到原本的 aws_instance 資源，修改 user_data 部分
# 我們要把 DB 的網址 (Endpoint) 傳進 Docker