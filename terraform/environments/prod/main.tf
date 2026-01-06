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

  # Remote state in S3 (RECOMENDADO para producción)
  backend "s3" {
    bucket         = "landa-terraform-state-prod"
    key            = "prod/apprunner.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "landa-terraform-locks"
  }
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
# Security Group for App Runner VPC Connector
# ============================================
resource "aws_security_group" "apprunner" {
  name        = "${var.project_name}-apprunner-sg"
  description = "Security group for App Runner VPC Connector to access RDS"
  vpc_id      = data.aws_vpc.default.id

  egress {
    description = "Allow outbound to RDS PostgreSQL"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-apprunner-sg"
  })
}

# ============================================
# VPC Connector for App Runner
# ============================================
resource "aws_apprunner_vpc_connector" "main" {
  count = var.create_rds && var.use_vpc_connector ? 1 : 0

  vpc_connector_name = "${var.project_name}-vpc-connector"
  subnets            = data.aws_subnets.default.ids
  security_groups     = [aws_security_group.apprunner.id]

  tags = var.tags
}

# ============================================
# Secrets Manager for Application Secrets
# ============================================
resource "aws_secretsmanager_secret" "database_url" {
  count = var.create_rds && var.use_secrets_manager ? 1 : 0

  name        = "${var.project_name}/database-url"
  description = "Database connection URL for ${var.project_name}"

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "database_url" {
  count = var.create_rds && var.use_secrets_manager ? 1 : 0

  secret_id = aws_secretsmanager_secret.database_url[0].id
  secret_string = var.create_rds ? module.rds[0].database_url : ""
}

resource "aws_secretsmanager_secret" "app_secrets" {
  count = var.use_secrets_manager ? 1 : 0

  name        = "${var.project_name}/app-secrets"
  description = "Application secrets (SECRET_KEY, STRIPE keys, etc.)"

  tags = var.tags
}

# Note: Secret values should be set manually or via AWS CLI/Console
# Example:
# aws secretsmanager put-secret-value \
#   --secret-id landa-beauty-api/app-secrets \
#   --secret-string '{"SECRET_KEY":"your-secret-key","STRIPE_SECRET_KEY":"sk_...","STRIPE_WEBHOOK_SECRET":"whsec_..."}'

# ============================================
# SNS Topic for Alerts
# ============================================
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"

  tags = var.tags
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ============================================
# CloudWatch Alarms
# ============================================
resource "aws_cloudwatch_metric_alarm" "app_runner_high_error_rate" {
  alarm_name          = "${var.project_name}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4xx"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Sum"
  threshold           = "100"
  alarm_description   = "Alert when 4xx error rate is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = module.apprunner.service_id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "app_runner_server_errors" {
  alarm_name          = "${var.project_name}-server-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5xx"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when 5xx server errors occur"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = module.apprunner.service_id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  count = var.create_rds ? 1 : 0

  alarm_name          = "${var.project_name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Alert when RDS CPU utilization is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = module.rds[0].instance_id
  }

  tags = var.tags
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

  # Secrets Manager configuration
  runtime_environment_secrets = var.use_secrets_manager && var.create_rds ? {
    DATABASE_URL = aws_secretsmanager_secret.database_url[0].arn
  } : {}

  secrets_manager_arns = var.use_secrets_manager && var.create_rds ? [
    aws_secretsmanager_secret.database_url[0].arn
  ] : []

  # VPC Connector for private RDS access
  vpc_connector_arn = var.create_rds && var.use_vpc_connector ? aws_apprunner_vpc_connector.main[0].arn : null

  # Pass DATABASE_URL as env var if not using Secrets Manager
  extra_env_vars = var.create_rds && !var.use_secrets_manager ? {
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
  # SECURITY: Restrict access to VPC only (App Runner will use VPC Connector if needed)
  vpc_id                      = data.aws_vpc.default.id
  subnet_ids                  = data.aws_subnets.default.ids
  allowed_cidr_blocks        = var.use_vpc_connector ? [] : [data.aws_vpc.default.cidr_block]  # Solo VPC si no hay VPC Connector
  allowed_security_group_ids = var.use_vpc_connector ? [aws_security_group.apprunner.id] : []  # Permitir desde App Runner SG
  publicly_accessible        = false  # SECURITY: RDS debe ser privado

  # Instance - Optimizado para empezar (puede escalar después)
  instance_class        = var.rds_instance_class
  allocated_storage     = 20   # Empezar con 20GB (optimización de costo)
  max_allocated_storage = 100  # Máximo 100GB (ajustar según necesidad)

  # Database
  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password

  # Production settings
  multi_az                = var.rds_multi_az
  deletion_protection     = true
  skip_final_snapshot     = false
  backup_retention_period  = 30  # 30 días de backups (mejor para producción)
  auto_minor_version_upgrade = true  # Actualizaciones automáticas de seguridad

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
  description = "CPU units for App Runner (256, 512, 1024, 2048, 4096)"
  default     = "1024"  # 1 vCPU - minimum for production workloads
}

variable "memory" {
  description = "Memory in MB for App Runner"
  default     = "2048"  # 2 GB RAM - minimum for production workloads
}

variable "min_instances" {
  default = 1
}

variable "max_instances" {
  description = "Maximum number of App Runner instances"
  default     = 5  # Optimizado: reducir de 10 a 5 inicialmente
}

variable "log_level" {
  default = "info"
}

variable "allowed_origins" {
  default = "https://landabeautysupply.com,https://www.landabeautysupply.com"
}

variable "tags" {
  description = "Tags for all resources"
  default = {
    Project     = "landa-beauty-supply"
    ManagedBy   = "terraform"
    Environment = "production"
    CostCenter  = "Engineering"
    BillingCode = "LAND-API-PROD"
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
  default     = "db.t3.micro"  # Optimizado: empezar pequeño, escalar si es necesario
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
# Infrastructure Configuration
# ============================================
variable "use_secrets_manager" {
  description = "Use AWS Secrets Manager for sensitive environment variables"
  type        = bool
  default     = true
}

variable "use_vpc_connector" {
  description = "Use VPC Connector for App Runner to access private RDS"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = ""
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

# ============================================
# Secrets Manager Outputs
# ============================================
output "database_secret_arn" {
  value       = var.create_rds && var.use_secrets_manager ? aws_secretsmanager_secret.database_url[0].arn : null
  description = "ARN of the database URL secret in Secrets Manager"
}

output "app_secrets_arn" {
  value       = var.use_secrets_manager ? aws_secretsmanager_secret.app_secrets[0].arn : null
  description = "ARN of the app secrets in Secrets Manager"
}

# ============================================
# Monitoring Outputs
# ============================================
output "sns_topic_arn" {
  value       = aws_sns_topic.alerts.arn
  description = "ARN of the SNS topic for alerts"
}

output "vpc_connector_arn" {
  value       = var.create_rds && var.use_vpc_connector ? aws_apprunner_vpc_connector.main[0].arn : null
  description = "ARN of the VPC Connector (if created)"
}

