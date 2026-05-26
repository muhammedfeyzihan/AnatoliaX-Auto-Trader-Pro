# ============================================================
# ecr-repo.tf — AnatoliaX ECR Repository (Terraform)
# ============================================================

# ECR Repository for AnatoliaX
resource "aws_ecr_repository" "anatoliax" {
  name                 = "anatoliax"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name        = "anatoliax"
    Environment = "production"
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "anatoliax" {
  repository = aws_ecr_repository.anatoliax.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 production images"
        selection = {
          tagStatus   = "tagged"
          tagPrefixList = ["prod"]
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 5 dev images"
        selection = {
          tagStatus   = "tagged"
          tagPrefixList = ["dev"]
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "Untagged images older than 7 days"
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

# Outputs
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.anatoliax.repository_url
}
