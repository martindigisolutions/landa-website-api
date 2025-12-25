# ============================================
# App Runner Module Variables
# ============================================

variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

# ============================================
# App Runner Configuration
# ============================================
variable "cpu" {
  description = "CPU units for App Runner (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "1024"
}

variable "memory" {
  description = "Memory in MB for App Runner (512, 1024, 2048, 3072, 4096, ...)"
  type        = string
  default     = "2048"
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

# ============================================
# Application Configuration
# ============================================
variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "info"
}

variable "allowed_origins" {
  description = "CORS allowed origins (comma-separated)"
  type        = string
  default     = "*"
}

variable "extra_env_vars" {
  description = "Additional environment variables to pass to the container"
  type        = map(string)
  default     = {}
}

# ============================================
# Tags
# ============================================
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

