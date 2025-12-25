# ============================================
# RDS Module Variables
# ============================================

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

# ============================================
# Network Configuration
# ============================================
variable "vpc_id" {
  description = "VPC ID where RDS will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for RDS subnet group"
  type        = list(string)
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to connect to RDS"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "publicly_accessible" {
  description = "Whether the RDS instance is publicly accessible"
  type        = bool
  default     = false
}

# ============================================
# Instance Configuration
# ============================================
variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.6"
}

variable "allocated_storage" {
  description = "Initial storage in GB"
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Maximum storage for autoscaling in GB"
  type        = number
  default     = 100
}

# ============================================
# Database Configuration
# ============================================
variable "db_name" {
  description = "Name of the database to create"
  type        = string
  default     = "landa_db"
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "landa_admin"
}

variable "db_password" {
  description = "Master password for the database"
  type        = string
  sensitive   = true
}

# ============================================
# Backup & Maintenance
# ============================================
variable "backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot when deleting"
  type        = bool
  default     = true
}

# ============================================
# Tags
# ============================================
variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

