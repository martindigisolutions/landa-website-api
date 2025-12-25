# ============================================
# Landa Beauty Supply API - DEV Environment
# ============================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Optional: Remote state in S3
  # backend "s3" {
  #   bucket  = "landa-terraform-state"
  #   key     = "dev/apprunner.tfstate"
  #   region  = "us-west-2"
  #   profile = "dev-account"
  # }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# ============================================
# Data Sources - Use Default VPC
# ============================================
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ============================================
# App Runner Module
# ============================================
module "apprunner" {
  source = "../../modules/apprunner"

  project_name = var.project_name
  environment  = "dev"

  # Resources
  cpu           = var.cpu
  memory        = var.memory
  min_instances = var.min_instances
  max_instances = var.max_instances

  # App Config
  log_level       = var.log_level
  allowed_origins = var.allowed_origins

  # Pass DATABASE_URL to App Runner
  extra_env_vars = var.create_rds ? {
    DATABASE_URL = module.rds[0].database_url
  } : {}

  tags = merge(var.tags, {
    Environment = "dev"
  })
}

# ============================================
# RDS PostgreSQL Module (Optional)
# ============================================
module "rds" {
  source = "../../modules/rds"
  count  = var.create_rds ? 1 : 0

  project_name = var.project_name
  environment  = "dev"

  # Network - Use default VPC
  vpc_id              = data.aws_vpc.default.id
  subnet_ids          = data.aws_subnets.default.ids
  allowed_cidr_blocks = ["0.0.0.0/0"]  # Dev: allow from anywhere (App Runner doesn't have fixed IP)
  publicly_accessible = true           # Dev: make accessible for testing

  # Instance - Small for dev
  instance_class        = "db.t3.micro"
  allocated_storage     = 20
  max_allocated_storage = 50

  # Database
  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password

  # Dev settings
  multi_az            = false
  deletion_protection = false
  skip_final_snapshot = true
  backup_retention_period = 1

  tags = merge(var.tags, {
    Environment = "dev"
  })
}

# ============================================
# Variables
# ============================================
variable "aws_region" {
  default = "us-west-2"
}

variable "aws_profile" {
  default = "dev-account"
}

variable "project_name" {
  default = "landa-beauty-api-dev"
}

variable "cpu" {
  default = "1024"
}

variable "memory" {
  default = "2048"
}

variable "min_instances" {
  default = 1
}

variable "max_instances" {
  default = 3
}

variable "log_level" {
  default = "debug"
}

variable "allowed_origins" {
  default = "http://localhost:3000,https://dev.landabeautysupply.com"
}

variable "tags" {
  default = {
    Project   = "landa-beauty-supply"
    ManagedBy = "terraform"
  }
}

# RDS Variables
variable "create_rds" {
  description = "Whether to create RDS instance"
  type        = bool
  default     = false
}

variable "db_name" {
  default = "landa_dev"
}

variable "db_username" {
  default = "landa_admin"
}

variable "db_password" {
  description = "Database password"
  type        = string
  default     = ""
  sensitive   = true
}

# ============================================
# Outputs
# ============================================
output "service_url" {
  value = module.apprunner.service_url
}

output "ecr_repository_url" {
  value = module.apprunner.ecr_repository_url
}

output "ecr_login_command" {
  value = "aws ecr get-login-password --region ${var.aws_region} --profile ${var.aws_profile} | docker login --username AWS --password-stdin ${module.apprunner.ecr_repository_url}"
}

# RDS Outputs (only when created)
output "rds_endpoint" {
  value       = var.create_rds ? module.rds[0].endpoint : null
  description = "RDS endpoint"
}

output "rds_database_url" {
  value       = var.create_rds ? module.rds[0].database_url : null
  sensitive   = true
  description = "Full database connection URL"
}

