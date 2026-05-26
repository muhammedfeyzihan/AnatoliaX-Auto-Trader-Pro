"""
AnatoliaX HFT Pro — Ultra Low Latency Execution Engine (v1.0)

Bu modül, AnatoliaX Trading System için kurumsal-kalitede HFT motorudur.
Mevcut PYTHON/hft/ modülünün yerine geçmez; onun yanında, daha düşük
gecikme gerektiren stratejiler için kullanılır.

Prompt: PROMPT_01_HFT_PRO_ULTRA_LOW_LATENCY.md
Kural Uyumu: K91-K97, K142-K148, K155-K158, K246-K248

Bileşenler:
- core: Nanosaniye saat, lock-free halka tampon, nesne havuzu, olay döngüsü
- feed: UDP çoklu yayın ayrıştırıcı, L3 emir defteri yeniden yapılandırma
- execution: Akıllı yönlendirici, dilimleme motoru, buzdağı algılayıcı
- latency: Çekirdek atlama, donanım zaman damgası, P99 izleyici
- strategy: Piyasa yapıcı, momentum keskin nişancı, spread scalper
- gpu: CUDA çekirdekleri, RAPIDS pipeline, ONNX çıkarımı
- backtest: Deterministik tekrar, piyasa etkisi modeli, BIST kayma modeli
- risk: <50μs acil durum anahtarı, ön-ticaret riski, kendi kendine ticaret önleme
"""

__version__ = "1.0.0"
