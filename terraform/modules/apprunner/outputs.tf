# ============================================
# App Runner Module Outputs
# ============================================

output "service_url" {
  description = "The URL of the App Runner service"
  value       = "https://${aws_apprunner_service.api.service_url}"
}

output "service_arn" {
  description = "The ARN of the App Runner service"
  value       = aws_apprunner_service.api.arn
}

output "service_id" {
  description = "The ID of the App Runner service"
  value       = aws_apprunner_service.api.service_id
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_repository_name" {
  description = "The name of the ECR repository"
  value       = aws_ecr_repository.api.name
}

