# ============================================
# Landa Beauty Supply API - PROD Environment
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
  #   bucket  = "landa-terraform-state-prod"
  #   key     = "prod/apprunner.tfstate"
  #   region  = "us-west-2"
  #   profile = "default"
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
  environment  = "prod"

  # Resources (more for production)
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
    Environment = "prod"
  })
}

# ============================================
# RDS PostgreSQL Module (Optional)
# ============================================
module "rds" {
  source = "../../modules/rds"
  count  = var.create_rds ? 1 : 0

  project_name = var.project_name
  environment  = "prod"

  # Network - Use default VPC
  vpc_id              = data.aws_vpc.default.id
  subnet_ids          = data.aws_subnets.default.ids
  allowed_cidr_blocks = ["0.0.0.0/0"]  # App Runner doesn't have fixed IP
  publicly_accessible = true

  # Instance - Larger for production
  instance_class        = var.rds_instance_class
  allocated_storage     = 50
  max_allocated_storage = 200

  # Database
  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password

  # Production settings
  multi_az                = var.rds_multi_az
  deletion_protection     = true
  skip_final_snapshot     = false
  backup_retention_period = 7

  tags = merge(var.tags, {
    Environment = "prod"
  })
}

# ============================================
# Variables
# ============================================
variable "aws_region" {
  default = "us-west-2"
}

variable "aws_profile" {
  default = "default"
}

variable "project_name" {
  default = "landa-beauty-api"
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
  default = 10
}

variable "log_level" {
  default = "info"
}

variable "allowed_origins" {
  default = "https://landabeautysupply.com,https://www.landabeautysupply.com"
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

variable "rds_instance_class" {
  description = "RDS instance class for production"
  default     = "db.t3.small"
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ for high availability"
  type        = bool
  default     = false
}

variable "db_name" {
  default = "landa_prod"
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

