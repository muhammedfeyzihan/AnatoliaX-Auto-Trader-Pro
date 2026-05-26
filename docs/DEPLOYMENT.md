# AnatoliaX Deployment Rehberi

Bu doküman AnatoliaX Trading System'in farklı ortamlara deployment'ını anlatır.

---

## İçindekiler

1. [Local Development](#local-development)
2. [Docker Compose](#docker-compose)
3. [Kubernetes](#kubernetes)
4. [AWS Cloud](#aws-cloud)
5. [Production Checklist](#production-checklist)

---

## Local Development

### Gereksinimler

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (opsiyonel, SQLite fallback)

### Kurulum

```bash
# 1. Repository clone
git clone https://github.com/anatoliax/AnatoliaX-Trading-System.git
cd AnatoliaX-Trading-System

# 2. Python bağımlılıkları
cd PYTHON
pip install -r requirements.txt

# 3. Node.js bağımlılıkları
cd ../SCRIPTS
npm install

# 4. Environment ayarları
cd ..
cp .env.example .env
# .env dosyasını düzenle (API key'leri ekle)

# 5. Veritabanı init
python PYTHON/main.py --init-db
```

### Çalıştırma

```bash
# Ana sistem
node SCRIPTS/main.js

# veya Python CLI
python PYTHON/main.py --scan THYAO,GARAN,ASELS

# Paper trading
AX_PAPER_TRADING=true python PYTHON/paper_trading/signal_engine.py

# Test
cd PYTHON && pytest tests/ -v
```

---

## Docker Compose

### Tüm Servisleri Başlat

```bash
# Build ve start
docker-compose up -d --build

# Logları izle
docker-compose logs -f

# Servis durumu
docker-compose ps

# Stop
docker-compose down
```

### Servisler

| Servis | Port | Açıklama |
|--------|------|----------|
| anatoliax-node | 3001, 8080 | Node.js ana motor |
| anatoliax-python | - | Python backtest |
| anatoliax-paper | - | Paper trading |
| anatoliax-telegram | - | Telegram reporter |
| anatoliax-execution | - | Live execution |
| anatoliax-scheduler | - | Cron jobs |
| postgres | 5432 | PostgreSQL |
| chromadb | 8000 | ChromaDB |
| redis | 6379 | Redis cache |
| prometheus | 9090 | Metrics |
| grafana | 3000 | Dashboard |

### .env Dosyası

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Grafana
GRAFANA_ADMIN_PASSWORD=admin

# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/anatoliax
```

---

## Kubernetes

### Önkoşullar

- Kubernetes cluster 1.28+
- kubectl configured
- Helm 3+ (opsiyonel)

### Deployment

```bash
# 1. Namespace oluştur
kubectl apply -f infrastructure/k8s/namespace.yaml

# 2. Secrets oluştur (gerçek değerlerle)
kubectl create secret generic anatoliax-secrets \
  --from-literal=DATABASE_PASSWORD='secure-password' \
  --from-literal=TELEGRAM_BOT_TOKEN='bot-token' \
  --from-literal=TELEGRAM_CHAT_ID='chat-id' \
  -n anatoliax

# 3. ConfigMap oluştur
kubectl apply -f infrastructure/k8s/configmap.yaml

# 4. PVC oluştur
kubectl apply -f infrastructure/k8s/pvc.yaml

# 5. Deployment'ları uygula
kubectl apply -f infrastructure/k8s/deployment.yaml

# 6. Services oluştur
kubectl apply -f infrastructure/k8s/service.yaml

# 7. Durum kontrol
kubectl get pods -n anatoliax
kubectl get services -n anatoliax
```

### HPA (Auto Scaling)

```bash
# HPA uygula
kubectl apply -f infrastructure/k8s/hpa.yaml

# Durum kontrol
kubectl get hpa -n anatoliax
```

### Ingress (External Access)

```bash
# Ingress uygula
kubectl apply -f infrastructure/k8s/ingress.yaml

# TLS certificate (cert-manager gerekli)
kubectl apply -f infrastructure/k8s/certificate.yaml
```

### Log ve Monitoring

```bash
# Pod logları
kubectl logs -f deployment/anatoliax-core -n anatoliax

# Metrikler
kubectl top pods -n anatoliax

# Event'ler
kubectl get events -n anatoliax --sort-by='.lastTimestamp'
```

---

## AWS Cloud

### Terraform ile Infrastructure

```bash
cd infrastructure/terraform

# Initialize
terraform init

# Plan
terraform plan -var="db_password=secure-password"

# Apply
terraform apply -var="db_password=secure-password"

# Outputs
terraform output
```

### Oluşturulan Kaynaklar

- **EKS Cluster** - Kubernetes 1.28
- **RDS PostgreSQL** - Managed database
- **ElastiCache Redis** - Managed cache
- **ECR Repository** - Container registry
- **S3 Bucket** - Backups, reports
- **CloudWatch** - Logging

### ECR'a Image Push

```bash
# Docker login
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-central-1.amazonaws.com

# Build ve push
docker build -t anatoliax .
docker tag anatoliax:latest <account-id>.dkr.ecr.eu-central-1.amazonaws.com/anatoliax:latest
docker push <account-id>.dkr.ecr.eu-central-1.amazonaws.com/anatoliax:latest
```

### EKS'e Deploy

```bash
# Kubeconfig update
aws eks update-kubeconfig --name anatoliax-cluster --region eu-central-1

# Deploy
kubectl apply -f infrastructure/k8s/
```

---

## Production Checklist

### Güvenlik

- [ ] Tüm secret'lar Secrets Manager'da
- [ ] API key'ler rotate edildi
- [ ] TLS sertifikaları geçerli
- [ ] Security group'lar doğru yapılandırıldı
- [ ] VPC flow logs aktif

### Monitoring

- [ ] Prometheus metrikleri akıyor
- [ ] Grafana dashboard'ları hazır
- [ ] Alert kuralları tanımlı
- [ ] Log aggregation (ELK) aktif
- [ ] Health check'ler çalışıyor

### Backup & Recovery

- [ ] RDS automated backup (7 gün)
- [ ] S3 versioning aktif
- [ ] Disaster recovery planı dokümante
- [ ] Checkpoint mekanizması test edildi

### Performance

- [ ] Load test yapıldı
- [ ] HPA kuralları ayarlandı
- [ ] Cache hit rate > 80%
- [ ] P99 latency < 500ms
- [ ] Error rate < 0.1%

### Compliance

- [ ] BIST regülasyon kontrolü aktif
- [ ] Audit log'lar immutable
- [ ] Data retention politikası uygulandı
- [ ] GDPR uyumluluk kontrolü

---

## Rollback

### Docker Compose

```bash
# Önceki versiyona dön
docker-compose pull anatoliax-node:previous-tag
docker-compose up -d anatoliax-node
```

### Kubernetes

```bash
# Deployment rollback
kubectl rollout undo deployment/anatoliax-core -n anatoliax

# Belirli revisona
kubectl rollout undo deployment/anatoliax-core -n anatoliax --to-revision=2

# Durum kontrol
kubectl rollout status deployment/anatoliax-core -n anatoliax
```

---

## Troubleshooting

### Pod CrashLoopBackOff

```bash
# Logları kontrol et
kubectl logs deployment/anatoliax-core -n anatoliax --previous

# Event'leri kontrol et
kubectl describe pod <pod-name> -n anatoliax

# Secrets var mı kontrol et
kubectl get secrets -n anatoliax
```

### Database Connection Error

```bash
# PostgreSQL çalışıyor mu
kubectl get pods -n anatoliax | grep postgres

# Connection test
kubectl run -it --rm --restart=Never postgres-test \
  --image=postgres:15 \
  --env="PGPASSWORD=password" \
  -- psql -h anatoliax-postgres -U postgres -d anatoliax -c "SELECT 1"
```

### High Latency

```bash
# Pod metrikleri
kubectl top pods -n anatoliax

# Network latency
kubectl exec -it <pod-name> -n anatoliax -- ping anatoliax-postgres

# Cache hit rate
curl http://localhost:3001/api/v1/metrics | jq '.cache_hit_rate'
```

---

## İletişim

- **GitHub Issues:** https://github.com/anatoliax/AnatoliaX-Trading-System/issues
- **Discord:** https://discord.gg/anatoliax
- **Dokümantasyon:** https://docs.anatoliax.com
