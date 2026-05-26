# ============================================================
# elasticache.tf — AnatoliaX ElastiCache Redis (Terraform)
# ============================================================

# Security Group for ElastiCache
resource "aws_security_group" "elasticache_sg" {
  name        = "${var.cluster_name}-elasticache-sg"
  description = "Security group for ElastiCache Redis"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
    description = "Redis from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-elasticache-sg"
  }
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.cluster_name}-redis-subnet"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Name = "${var.cluster_name}-redis-subnet"
  }
}

# ElastiCache Redis Cluster
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "${var.cluster_name}-redis"
  description                   = "AnatoliaX Redis replication group"
  node_type                     = "cache.t3.medium"
  num_cache_clusters            = 2
  automatic_failover_enabled    = true
  multi_az_enabled              = true

  subnet_group_name             = aws_elasticache_subnet_group.redis.name
  security_group_ids            = [aws_security_group.elasticache_sg.id]

  parameter_group_name          = aws_elasticache_parameter_group.redis.name
  port                          = 6379

  at_rest_encryption_enabled    = true
  transit_encryption_enabled    = true
  auth_token                    = var.redis_auth_token

  snapshot_retention_limit      = 7
  snapshot_window               = "03:00-04:00"
  maintenance_window            = "Mon:04:00-Mon:05:00"

  tags = {
    Name        = "${var.cluster_name}-redis"
    Environment = "production"
  }
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "redis" {
  family = "redis7"
  name   = "${var.cluster_name}-redis-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = {
    Name = "${var.cluster_name}-redis-params"
  }
}

# Variable for Redis auth token
variable "redis_auth_token" {
  description = "Redis authentication token"
  type        = string
  sensitive   = true
}

# Outputs
output "elasticache_primary_endpoint" {
  description = "ElastiCache primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "elasticache_reader_endpoint" {
  description = "ElastiCache reader endpoint"
  value       = aws_elasticache_replication_group.redis.reader_endpoint_address
}
