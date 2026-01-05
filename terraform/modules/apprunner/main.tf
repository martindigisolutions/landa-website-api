# ============================================
# App Runner Module
# Reusable module for ECR + App Runner deployment
# ============================================

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

# ECR Lifecycle Policy - Keep last 5 images
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
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

# IAM Policy para acceso a Secrets Manager y SSM
resource "aws_iam_role_policy" "apprunner_secrets" {
  name = "${var.project_name}-apprunner-secrets-policy"
  role = aws_iam_role.apprunner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = var.secrets_manager_arns
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = var.ssm_parameter_arns
      }
    ]
  })
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

        # Environment variables (non-sensitive)
        runtime_environment_variables = merge(
          {
            PORT            = "8080"
            ALGORITHM       = "HS256"
            LOG_LEVEL       = var.log_level
            ALLOWED_ORIGINS = var.allowed_origins
            ENVIRONMENT     = var.environment
          },
          var.extra_env_vars
        )

        # Secrets from Secrets Manager (sensitive)
        runtime_environment_secrets = var.runtime_environment_secrets
      }

      image_identifier      = "${aws_ecr_repository.api.repository_url}:latest"
      image_repository_type = "ECR"
    }

    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu               = var.cpu
    memory            = var.memory
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.api.arn

  # VPC Connector (optional, for private RDS access)
  dynamic "network_configuration" {
    for_each = var.vpc_connector_arn != null ? [1] : []
    content {
      egress_configuration {
        egress_type       = "VPC"
        vpc_connector_arn = var.vpc_connector_arn
      }
    }
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/api/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  tags = var.tags

  depends_on = [
    aws_iam_role_policy_attachment.apprunner_ecr_policy,
    aws_iam_role_policy.apprunner_secrets
  ]
}

# ============================================
# Auto Scaling Configuration
# ============================================
resource "aws_apprunner_auto_scaling_configuration_version" "api" {
  auto_scaling_configuration_name = "${var.project_name}-autoscale"

  min_size        = var.min_instances
  max_size        = var.max_instances
  max_concurrency = var.max_concurrency

  tags = var.tags
}

