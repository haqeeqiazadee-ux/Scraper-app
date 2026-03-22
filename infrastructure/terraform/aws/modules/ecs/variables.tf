variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "public_subnet_ids" {
  description = "IDs of public subnets for the ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "IDs of private subnets for ECS tasks"
  type        = list(string)
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate for HTTPS"
  type        = string
}

variable "service_names" {
  description = "List of service names to deploy"
  type        = list(string)
  default     = ["control-plane", "worker-http", "worker-browser", "worker-ai"]
}

variable "ecr_repository_urls" {
  description = "Map of service name to ECR repository URL"
  type        = map(string)
}

variable "container_port" {
  description = "Port the application listens on"
  type        = number
  default     = 8000
}

variable "task_cpu" {
  description = "Fargate task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory in MiB"
  type        = number
  default     = 1024
}

variable "control_plane_desired_count" {
  description = "Desired number of control-plane tasks"
  type        = number
  default     = 2
}

variable "control_plane_max_count" {
  description = "Max number of control-plane tasks for auto-scaling"
  type        = number
  default     = 6
}

variable "worker_desired_count" {
  description = "Desired number of worker tasks per service"
  type        = number
  default     = 1
}

variable "database_endpoint" {
  description = "RDS database endpoint (host:port)"
  type        = string
}

variable "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 artifacts bucket"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 artifacts bucket"
  type        = string
}
