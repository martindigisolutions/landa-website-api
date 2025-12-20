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

output "auto_deploy_enabled" {
  description = "Auto-deploy on git push"
  value       = var.auto_deploy
}
