###############################################################################
# Root Module — AI Scraping Platform AWS Infrastructure
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and configure for remote state
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "scraper-platform/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ---------------------------------------------------------------------------
# Data Sources
# ---------------------------------------------------------------------------
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------
module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  environment          = var.environment
  region               = var.region
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

# ---------------------------------------------------------------------------
# S3 — Artifact Storage
# ---------------------------------------------------------------------------
module "s3" {
  source = "./modules/s3"

  project_name         = var.project_name
  environment          = var.environment
  account_id           = data.aws_caller_identity.current.account_id
  cors_allowed_origins = var.cors_allowed_origins
}

# ---------------------------------------------------------------------------
# RDS — PostgreSQL
# ---------------------------------------------------------------------------
module "rds" {
  source = "./modules/rds"

  project_name               = var.project_name
  environment                = var.environment
  vpc_id                     = module.vpc.vpc_id
  private_subnet_ids         = module.vpc.private_subnet_ids
  allowed_security_group_ids = [module.ecs.ecs_tasks_security_group_id]
  instance_class             = var.rds_instance_class
  allocated_storage          = var.rds_allocated_storage
  max_allocated_storage      = var.rds_max_allocated_storage
  database_name              = var.database_name
  database_username          = var.database_username
  database_password          = var.database_password
  multi_az                   = var.rds_multi_az
  backup_retention_period    = var.rds_backup_retention_period
}

# ---------------------------------------------------------------------------
# ElastiCache — Redis
# ---------------------------------------------------------------------------
module "redis" {
  source = "./modules/redis"

  project_name               = var.project_name
  environment                = var.environment
  vpc_id                     = module.vpc.vpc_id
  private_subnet_ids         = module.vpc.private_subnet_ids
  allowed_security_group_ids = [module.ecs.ecs_tasks_security_group_id]
  node_type                  = var.redis_node_type
  num_cache_clusters         = var.redis_num_cache_clusters
  auth_token                 = var.redis_auth_token
}

# ---------------------------------------------------------------------------
# ECR — Container Image Repositories
# ---------------------------------------------------------------------------
resource "aws_ecr_repository" "services" {
  for_each = toset(var.service_names)

  name                 = "${var.project_name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Environment = var.environment
    Service     = each.key
  }
}

resource "aws_ecr_lifecycle_policy" "services" {
  for_each = toset(var.service_names)

  repository = aws_ecr_repository.services[each.key].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 20 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 20
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# ECS — Fargate Cluster + Services
# ---------------------------------------------------------------------------
module "ecs" {
  source = "./modules/ecs"

  project_name        = var.project_name
  environment         = var.environment
  region              = var.region
  vpc_id              = module.vpc.vpc_id
  public_subnet_ids   = module.vpc.public_subnet_ids
  private_subnet_ids  = module.vpc.private_subnet_ids
  certificate_arn     = var.certificate_arn
  service_names       = var.service_names
  task_cpu            = var.ecs_task_cpu
  task_memory         = var.ecs_task_memory
  container_port      = var.container_port
  database_endpoint   = module.rds.endpoint
  redis_endpoint      = module.redis.primary_endpoint
  s3_bucket_name      = module.s3.bucket_name
  s3_bucket_arn       = module.s3.bucket_arn

  control_plane_desired_count = var.ecs_control_plane_desired_count
  control_plane_max_count     = var.ecs_control_plane_max_count
  worker_desired_count        = var.ecs_worker_desired_count

  ecr_repository_urls = {
    for name in var.service_names :
    name => aws_ecr_repository.services[name].repository_url
  }
}
