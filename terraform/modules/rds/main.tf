# ============================================
# RDS PostgreSQL Module
# ============================================

# ============================================
# Security Group for RDS
# ============================================
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id

  # Allow from CIDR blocks
  dynamic "ingress" {
    for_each = length(var.allowed_cidr_blocks) > 0 ? [1] : []
    content {
      description = "PostgreSQL from VPC CIDR"
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = var.allowed_cidr_blocks
    }
  }

  # Allow from security groups (for App Runner VPC Connector)
  dynamic "ingress" {
    for_each = var.allowed_security_group_ids
    content {
      description     = "PostgreSQL from security group"
      from_port       = 5432
      to_port         = 5432
      protocol        = "tcp"
      security_groups = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-rds-sg"
  })
}

# ============================================
# DB Parameter Group (for SSL enforcement)
# ============================================
resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-pg"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"  # Force SSL connections
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-pg"
  })
}

# ============================================
# DB Subnet Group
# ============================================
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${var.project_name}-db-subnet"
  })
}

# ============================================
# RDS PostgreSQL Instance
# ============================================
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-db"

  # Engine
  engine               = "postgres"
  engine_version       = var.engine_version
  instance_class       = var.instance_class
  
  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.publicly_accessible

  # Parameter Group (for SSL enforcement)
  parameter_group_name = aws_db_parameter_group.main.name

  # Backup
  backup_retention_period = var.backup_retention_period
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  copy_tags_to_snapshot  = true  # Copy tags to snapshots for better tracking

  # Options
  multi_az                  = var.multi_az
  deletion_protection       = var.deletion_protection
  skip_final_snapshot      = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.project_name}-final-snapshot"
  auto_minor_version_upgrade = var.auto_minor_version_upgrade

  # Performance Insights (free for db.t3.micro)
  performance_insights_enabled = var.instance_class != "db.t3.micro"

  # Logging
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = var.tags
}

