# ============================================
# Landa Beauty Supply API - AWS App Runner
# Terraform Configuration (ECR + Docker)
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
# ECR Repository
# ============================================
resource "aws_ecr_repository" "api" {
  name                 = "${var.project_name}-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# ============================================
# IAM Role para App Runner (acceso a ECR)
# ============================================
resource "aws_iam_role" "apprunner_ecr_access" {
  name = "${var.project_name}-apprunner-ecr-role"

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

resource "aws_iam_role_policy_attachment" "apprunner_ecr_policy" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
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
# App Runner Service (desde ECR)
# ============================================
resource "aws_apprunner_service" "api" {
  service_name = "${var.project_name}-api"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_configuration {
        port = "8080"

        runtime_environment_variables = {
          PORT            = "8080"
          ALGORITHM       = "HS256"
          LOG_LEVEL       = var.log_level
          ALLOWED_ORIGINS = var.allowed_origins
        }
      }

      image_identifier      = "${aws_ecr_repository.api.repository_url}:latest"
      image_repository_type = "ECR"
    }

    auto_deployments_enabled = true
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

  depends_on = [aws_iam_role_policy_attachment.apprunner_ecr_policy]
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

