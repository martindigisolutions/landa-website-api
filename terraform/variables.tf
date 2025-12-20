# ============================================
# Variables
# ============================================

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use (run 'aws configure list-profiles' to see available profiles)"
  type        = string
  default     = "default"
}

variable "project_name" {
  description = "Project name (used for naming resources)"
  type        = string
  default     = "landa-beauty"
}

# ============================================
# GitHub Configuration
# ============================================

variable "github_connection_arn" {
  description = "ARN of the GitHub connection (create in AWS Console first)"
  type        = string
  # Ejemplo: arn:aws:apprunner:us-east-1:123456789:connection/github-connection/abc123
}

variable "github_repository_url" {
  description = "GitHub repository URL"
  type        = string
  # Ejemplo: https://github.com/tu-usuario/landa-website-api
}

variable "github_branch" {
  description = "GitHub branch to deploy"
  type        = string
  default     = "main"
}

variable "source_directory" {
  description = "Source directory in the repository (where Dockerfile is located)"
  type        = string
  default     = "/"
}

variable "auto_deploy" {
  description = "Enable automatic deployments on push"
  type        = bool
  default     = true
}

# ============================================
# App Runner Configuration
# ============================================

variable "cpu" {
  description = "CPU units for App Runner (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "1024"  # 1 vCPU
}

variable "memory" {
  description = "Memory in MB for App Runner (512, 1024, 2048, 3072, 4096, 6144, 8192, 10240, 12288)"
  type        = string
  default     = "2048"  # 2 GB
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 5
}

variable "max_concurrency" {
  description = "Maximum concurrent requests per instance"
  type        = number
  default     = 100
}

variable "log_level" {
  description = "Log level (debug, info, warning, error)"
  type        = string
  default     = "info"
}

# ============================================
# Application Configuration
# ============================================

variable "allowed_origins" {
  description = "Allowed CORS origins (comma-separated)"
  type        = string
  default     = "https://landabeautysupply.com"
}

# ============================================
# Secrets Configuration
# ============================================

variable "use_ssm_secrets" {
  description = "Use SSM Parameter Store for secrets (recommended for production)"
  type        = bool
  default     = true
}

variable "database_url" {
  description = "PostgreSQL connection string"
  type        = string
  sensitive   = true
  default     = ""
}

variable "secret_key" {
  description = "JWT Secret Key (32+ characters)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "stripe_secret_key" {
  description = "Stripe Secret Key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "stripe_webhook_secret" {
  description = "Stripe Webhook Secret"
  type        = string
  sensitive   = true
  default     = ""
}

# ============================================
# Tags
# ============================================

variable "tags" {
  description = "Tags for all resources"
  type        = map(string)
  default = {
    Project     = "landa-beauty-supply"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
