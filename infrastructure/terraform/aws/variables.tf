###############################################################################
# Input Variables — AI Scraping Platform AWS Infrastructure
###############################################################################

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
variable "region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "scraper-platform"
}

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "domain_name" {
  description = "Domain name for the platform (e.g., scraper.example.com)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate for HTTPS on the ALB"
  type        = string
}

variable "cors_allowed_origins" {
  description = "Allowed origins for S3 CORS configuration"
  type        = list(string)
  default     = ["https://*.example.com"]
}

# ---------------------------------------------------------------------------
# RDS — PostgreSQL
# ---------------------------------------------------------------------------
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "rds_allocated_storage" {
  description = "Initial allocated storage for RDS in GB"
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage" {
  description = "Maximum storage for RDS autoscaling in GB"
  type        = number
  default     = 100
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ for RDS"
  type        = bool
  default     = true
}

variable "rds_backup_retention_period" {
  description = "Number of days to retain RDS backups"
  type        = number
  default     = 7
}

variable "database_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "scraper_platform"
}

variable "database_username" {
  description = "Master username for the RDS instance"
  type        = string
  sensitive   = true
}

variable "database_password" {
  description = "Master password for the RDS instance"
  type        = string
  sensitive   = true
}

# ---------------------------------------------------------------------------
# ElastiCache — Redis
# ---------------------------------------------------------------------------
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t4g.medium"
}

variable "redis_num_cache_clusters" {
  description = "Number of cache clusters (nodes) in the Redis replication group"
  type        = number
  default     = 2
}

variable "redis_auth_token" {
  description = "Auth token for Redis (must be at least 16 characters)"
  type        = string
  sensitive   = true
}

# ---------------------------------------------------------------------------
# ECS — Fargate
# ---------------------------------------------------------------------------
variable "service_names" {
  description = "List of ECS service names to deploy"
  type        = list(string)
  default     = ["control-plane", "worker-http", "worker-browser", "worker-ai"]
}

variable "ecs_task_cpu" {
  description = "Fargate task CPU units (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "Fargate task memory in MiB"
  type        = number
  default     = 1024
}

variable "ecs_control_plane_desired_count" {
  description = "Desired number of control-plane tasks"
  type        = number
  default     = 2
}

variable "ecs_control_plane_max_count" {
  description = "Maximum number of control-plane tasks for auto-scaling"
  type        = number
  default     = 6
}

variable "ecs_worker_desired_count" {
  description = "Desired number of worker tasks per service"
  type        = number
  default     = 1
}

variable "container_port" {
  description = "Port that application containers listen on"
  type        = number
  default     = 8000
}
