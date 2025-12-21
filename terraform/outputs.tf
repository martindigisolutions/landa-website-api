# ============================================
# Outputs
# ============================================

output "app_runner_url" {
  description = "App Runner service URL"
  value       = "https://${aws_apprunner_service.api.service_url}"
}

output "app_runner_arn" {
  description = "App Runner service ARN"
  value       = aws_apprunner_service.api.arn
}

output "app_runner_service_id" {
  description = "App Runner service ID"
  value       = aws_apprunner_service.api.service_id
}

output "health_check_url" {
  description = "Health check endpoint"
  value       = "https://${aws_apprunner_service.api.service_url}/api/health"
}

output "ecr_repository_url" {
  description = "ECR repository URL - use this to push Docker images"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_login_command" {
  description = "Command to login to ECR"
  value       = "aws ecr get-login-password --region ${var.aws_region} --profile ${var.aws_profile} | docker login --username AWS --password-stdin ${aws_ecr_repository.api.repository_url}"
}

output "docker_push_commands" {
  description = "Commands to build and push Docker image"
  value       = <<-EOT
    # Build image
    docker build -t ${var.project_name}-api .
    
    # Tag image
    docker tag ${var.project_name}-api:latest ${aws_ecr_repository.api.repository_url}:latest
    
    # Push image
    docker push ${aws_ecr_repository.api.repository_url}:latest
  EOT
}
