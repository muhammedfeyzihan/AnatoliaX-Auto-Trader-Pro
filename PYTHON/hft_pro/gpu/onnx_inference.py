"""
gpu/onnx_inference.py — GPU hizlandirilmis model cikarsama (alt-ms)
"""
from typing import Optional


class ONNXInference:
    """
    ONNX Runtime GPU cikarsama.

    Kullanim:
        inf = ONNXInference("models/signal_classifier.onnx")
        outputs = inf.infer(inputs)

    Hedef: < 1ms cikarsama (GPU).
    Geri donus: CPUExecutionProvider.
    """

    def __init__(self, model_path: str, providers: list = None):
        self.model_path = model_path
        self.providers = providers or ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
        self._session = None

    def load(self) -> bool:
        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(self.model_path, providers=self.providers)
            return True
        except Exception:
            return False

    def infer(self, inputs: dict) -> Optional[list]:
        if self._session is None:
            return None
        return self._session.run(None, inputs)
