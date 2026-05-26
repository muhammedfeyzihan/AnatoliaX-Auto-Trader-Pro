# AnatoliaX API Dokümantasyonu

## Genel Bakış

AnatoliaX, hem gRPC hem de REST API arayüzleri sunan çok katmanlı bir trading sistemidir.

---

## gRPC API

### Servis Tanımı

```protobuf
// anatoliax_grpc/anatoliax.proto
service AnatoliaXService {
  // Sinyal analizi
  rpc AnalyzeSymbol(SymbolRequest) returns (SymbolResponse);
  
  // Portföy durumu
  rpc GetPortfolio(PortfolioRequest) returns (PortfolioResponse);
  
  // Emir gönderme
  rpc SubmitOrder(OrderRequest) returns (OrderResponse);
  
  // Risk kontrolü
  rpc CheckRisk(RiskRequest) returns (RiskResponse);
  
  // Strateji listesi
  rpc ListStrategies(Empty) returns (StrategiesResponse);
}
```

### Kullanım (Python)

```python
from PYTHON.anatoliax_grpc.client import AnatoliaXClient

client = AnatoliaXClient(host='localhost', port=50051)

# Sinyal analizi
response = client.analyze_symbol('THYAO')
print(f"Signal: {response.signal}, Confidence: {response.confidence}")

# Portföy durumu
portfolio = client.get_portfolio()
print(f"Total Value: {portfolio.total_value}, PnL: {portfolio.daily_pnl}")

# Emir gönderme
order = client.submit_order(
    symbol='THYAO',
    side='BUY',
    size=100,
    price=95.50,
    stop_loss=90.00
)
print(f"Order ID: {order.id}, Status: {order.status}")
```

### Kullanım (Node.js)

```javascript
const { AnatoliaXClient } = require('./SCRIPTS/core/grpc_client.js');

const client = new AnatoliaXClient('localhost', 50051);

// Sinyal analizi
const response = await client.analyzeSymbol('THYAO');
console.log(`Signal: ${response.signal}, Confidence: ${response.confidence}`);
```

---

## REST API

### Endpoint'ler

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/health` | Sağlık kontrolü |
| GET | `/api/v1/symbols` | Sembol listesi |
| GET | `/api/v1/symbols/{symbol}` | Sembol analizi |
| POST | `/api/v1/signals/scan` | Sinyal taraması |
| GET | `/api/v1/portfolio` | Portföy durumu |
| POST | `/api/v1/orders` | Emir oluştur |
| GET | `/api/v1/orders/{id}` | Emir durumu |
| DELETE | `/api/v1/orders/{id}` | Emir iptal |
| GET | `/api/v1/risk/status` | Risk durumu |
| GET | `/api/v1/strategies` | Strateji listesi |
| POST | `/api/v1/strategies/{name}/run` | Strateji çalıştır |
| GET | `/api/v1/metrics` | Prometheus metrikleri |

### Örnek İstekler

#### Sağlık Kontrolü

```bash
curl http://localhost:3001/api/v1/health
```

```json
{
  "status": "healthy",
  "version": "3.3",
  "uptime_seconds": 86400,
  "services": {
    "database": "connected",
    "redis": "connected",
    "chromadb": "connected"
  }
}
```

#### Sinyal Taraması

```bash
curl -X POST http://localhost:3001/api/v1/signals/scan \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["THYAO", "GARAN", "ASELS"], "min_confidence": 0.7}'
```

```json
{
  "scan_id": "scan_12345",
  "timestamp": "2026-05-24T10:30:00Z",
  "signals": [
    {
      "symbol": "THYAO",
      "signal": "BUY",
      "confidence": 0.85,
      "entry_price": 95.50,
      "stop_loss": 90.00,
      "take_profit": 105.00,
      "rr_ratio": 2.5
    }
  ]
}
```

#### Emir Oluşturma

```bash
curl -X POST http://localhost:3001/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{
    "symbol": "THYAO",
    "side": "BUY",
    "size": 100,
    "type": "LIMIT",
    "price": 95.50,
    "stop_loss": 90.00,
    "take_profit": 105.00
  }'
```

```json
{
  "order_id": "ord_67890",
  "status": "PENDING",
  "symbol": "THYAO",
  "side": "BUY",
  "size": 100,
  "price": 95.50,
  "created_at": "2026-05-24T10:35:00Z"
}
```

---

## WebSocket API

### Bağlantı

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
  console.log('Connected to AnatoliaX WebSocket');
  
  // Subscribe to signals
  ws.send(JSON.stringify({
    type: 'SUBSCRIBE',
    channel: 'signals',
    symbols: ['THYAO', 'GARAN']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Mesaj Tipleri

| Type | Channel | Açıklama |
|------|---------|----------|
| `SUBSCRIBE` | `signals` | Sinyal aboneliği |
| `SUBSCRIBE` | `trades` | İşlem aboneliği |
| `SUBSCRIBE` | `portfolio` | Portföy aboneliği |
| `UNSUBSCRIBE` | `*` | Abonelik iptali |
| `PING` | `*` | Bağlantı testi |

---

## Hata Kodları

| Kod | Açıklama |
|-----|----------|
| 400 | Geçersiz istek |
| 401 | Yetkilendirme hatası |
| 403 | Erişim reddedildi |
| 404 | Kaynak bulunamadı |
| 429 | Rate limit aşıldı |
| 500 | Sunucu hatası |
| 503 | Servis kullanılamıyor |

---

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/api/v1/health` | 60/dk |
| `/api/v1/symbols/*` | 100/dk |
| `/api/v1/signals/*` | 30/dk |
| `/api/v1/orders/*` | 60/dk |
| `/ws` | 1000/dk |

---

## Authentication

API anahtarı header ile gönderilmelidir:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:3001/api/v1/portfolio
```

API anahtarı oluşturmak için:

```python
from PYTHON.auth.api_key_manager import APIKeyManager

manager = APIKeyManager()
key = manager.create_key(name="my-app", permissions=["read", "trade"])
print(key)
```
