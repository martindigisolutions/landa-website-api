# ============================================
# Landa Beauty Supply API - AWS App Runner
# Terraform Configuration (Dockerfile from GitHub)
# ============================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# ============================================
# IAM Role para App Runner (acceso a ECR - necesario para builds)
# ============================================
resource "aws_iam_role" "apprunner_build" {
  name = "${var.project_name}-apprunner-build-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# ============================================
# IAM Role para la instancia de App Runner
# ============================================
resource "aws_iam_role" "apprunner_instance" {
  name = "${var.project_name}-apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# ============================================
# App Runner Service (Dockerfile desde GitHub)
# ============================================
resource "aws_apprunner_service" "api" {
  service_name = "${var.project_name}-api"

  source_configuration {
    authentication_configuration {
      connection_arn = var.github_connection_arn
    }

    code_repository {
      repository_url   = var.github_repository_url
      source_directory = var.source_directory

      source_code_version {
        type  = "BRANCH"
        value = var.github_branch
      }

      code_configuration {
        # Usa el apprunner.yaml del repositorio para detectar Dockerfile
        configuration_source = "REPOSITORY"
      }
    }

    auto_deployments_enabled = var.auto_deploy
  }

  instance_configuration {
    cpu    = var.cpu
    memory = var.memory
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.api.arn

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/api/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  tags = var.tags
}

# ============================================
# Auto Scaling Configuration
# ============================================
resource "aws_apprunner_auto_scaling_configuration_version" "api" {
  auto_scaling_configuration_name = "landa-api-autoscale"

  min_size        = var.min_instances
  max_size        = var.max_instances
  max_concurrency = var.max_concurrency

  tags = var.tags
}
