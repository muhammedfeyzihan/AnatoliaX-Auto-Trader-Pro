# AWS Infrastructure for AnatoliaX

Bu dizin AWS cloud infrastructure kodlarını içerir.

## Kullanılan Servisler

- **EKS** - Kubernetes cluster
- **RDS** - PostgreSQL veritabanı
- **ElastiCache** - Redis cache
- **ECR** - Docker container registry
- **CloudWatch** - Logging ve monitoring
- **Secrets Manager** - API key ve secret yönetimi

## Kurulum

```bash
# Terraform ile
cd ../terraform
terraform init
terraform apply

# AWS CLI ile
aws eks create-cluster --name anatoliax --version 1.28
```

## Dizin Yapısı

```
aws/
├── README.md           # Bu dosya
├── eks-cluster.tf      # EKS cluster tanımı (Terraform)
├── rds-postgres.tf     # RDS PostgreSQL tanımı
├── elasticache.tf      # ElastiCache Redis tanımı
├── ecr-repo.tf         # ECR repository tanımı
└── vpc.tf              # VPC yapılandırması
```
