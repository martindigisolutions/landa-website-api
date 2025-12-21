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

  # Extra env vars (secrets should be added manually in App Runner console)
  extra_env_vars = {}

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
