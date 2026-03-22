###############################################################################
# Outputs — AI Scraping Platform AWS Infrastructure
###############################################################################

# ---------------------------------------------------------------------------
# API / Networking
# ---------------------------------------------------------------------------
output "api_endpoint_url" {
  description = "HTTPS endpoint for the API (ALB DNS name)"
  value       = module.ecs.api_endpoint_url
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.ecs.alb_dns_name
}

output "alb_zone_id" {
  description = "Route 53 zone ID of the ALB (for alias records)"
  value       = module.ecs.alb_zone_id
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

# ---------------------------------------------------------------------------
# RDS
# ---------------------------------------------------------------------------
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port)"
  value       = module.rds.endpoint
}

output "rds_address" {
  description = "RDS PostgreSQL hostname"
  value       = module.rds.address
}

output "rds_database_name" {
  description = "Name of the PostgreSQL database"
  value       = module.rds.database_name
}

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = module.redis.primary_endpoint
}

output "redis_reader_endpoint" {
  description = "ElastiCache Redis reader endpoint"
  value       = module.redis.reader_endpoint
}

# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------
output "s3_bucket_name" {
  description = "Name of the S3 artifacts bucket"
  value       = module.s3.bucket_name
}

output "s3_bucket_arn" {
  description = "ARN of the S3 artifacts bucket"
  value       = module.s3.bucket_arn
}

# ---------------------------------------------------------------------------
# ECR
# ---------------------------------------------------------------------------
output "ecr_repository_urls" {
  description = "Map of service name to ECR repository URL"
  value = {
    for name in var.service_names :
    name => aws_ecr_repository.services[name].repository_url
  }
}

# ---------------------------------------------------------------------------
# ECS
# ---------------------------------------------------------------------------
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}
