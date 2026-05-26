"""
gpu/onnx_runtime.py — ONNX Runtime GPU cikarsama (TensorRT/CUDA saglayicilari)
"""
from typing import Optional


class ONNXGPUInference:
    """
    ONNX Runtime GPU cikarsama motoru.

    Saglayicilar (oncelik siralamasi):
    1. TensorRT (en hizli, NVIDIA GPU gerekli)
    2. CUDAExecutionProvider (genel NVIDIA GPU)
    3. CPUExecutionProvider (geri donus)

    Kullanim:
        inf = ONNXGPUInference("model.onnx")
        outputs = inf.predict(inputs)
    """

    def __init__(self, model_path: str, providers: list = None):
        self.model_path = model_path
        self._providers = providers or ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
        self._session = None

    def load(self) -> bool:
        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(self.model_path, providers=self._providers)
            return True
        except Exception:
            return False

    def predict(self, inputs: dict) -> Optional[list]:
        if self._session is None:
            return None
        return self._session.run(None, inputs)
