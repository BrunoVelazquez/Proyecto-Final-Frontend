from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional


# ══════════════════════════════════════════════════════════════════════════════
# 1. Estructuras de datos del contrato
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Detection:
    """Una detección individual devuelta por el modelo."""
    category: str
    score: float
    bbox: List[float]   # [x1, y1, x2, y2]

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "score": round(self.score, 3),
            "bbox": self.bbox,
        }


@dataclass
class PredictionResult:
    """
    Resultado estándar de inferencia.
    Independiente del modelo concreto utilizado.
    """
    detections: List[Detection]
    model_source: str           # "default" | "local"
    model_name: str             # nombre del archivo .pt
    raw: Any = field(default=None, repr=False)  # objeto SAHI crudo (para export_visuals)

    @property
    def total(self) -> int:
        return len(self.detections)

    def to_dict(self) -> dict:
        return {
            "total_detections": self.total,
            "model_source": self.model_source,
            "model_name": self.model_name,
            "detections": [d.to_dict() for d in self.detections],
        }



class BaseModelAdapter(ABC):
    """
    Interfaz estándar que todo adaptador de modelo debe implementar.

    Reglas del contrato:
    ─────────────────────
    • `load()` debe inicializar el modelo y dejarlo listo para inferencia.
    • `predict()` siempre devuelve un `PredictionResult`.
    • El adaptador NO decide si el modelo es "default" o "local";
      esa responsabilidad pertenece a `ModelService`.
    • La implementación puede cachear internamente el modelo cargado.
    """

    def __init__(self, model_path: str, confidence: float, device: str):
        self.model_path = model_path
        self.confidence = confidence
        self.device = device
        self._model = None          # instancia interna del modelo cargado
        self._config_hash: str = self._hash_config()

    # ── Métodos abstractos (obligatorios en subclases) ─────────────────────

    @abstractmethod
    def load(self) -> None:
        """
        Carga el modelo en memoria.
        Debe asignar la instancia a `self._model`.
        """

    @abstractmethod
    def predict(
        self,
        image_path: str,
        slice_height: int = 512,
        slice_width: int = 512,
        overlap_height: float = 0.2,
        overlap_width: float = 0.2,
    ) -> PredictionResult:
        """
        Ejecuta inferencia sobre `image_path`.
        Siempre retorna un `PredictionResult`.
        """

    # ── Métodos base (disponibles para subclases) ──────────────────────────

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def ensure_loaded(self) -> None:
        """Carga el modelo si aún no está en memoria."""
        if not self.is_loaded:
            self.load()

    def invalidate_cache(self) -> None:
        """Descarga el modelo de memoria (fuerza recarga en próxima predicción)."""
        self._model = None

    def _hash_config(self) -> str:
        """Hash único de la configuración actual para detectar cambios."""
        key = f"{self.model_path}|{self.confidence}|{self.device}"
        return hashlib.md5(key.encode()).hexdigest()

    def __repr__(self) -> str:
        status = "cargado" if self.is_loaded else "no cargado"
        return (
            f"{self.__class__.__name__}("
            f"model='{Path(self.model_path).name}', "
            f"device='{self.device}', "
            f"conf={self.confidence}, "
            f"status={status})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 3. Implementación concreta — YOLOv8SAHIAdapter
# ══════════════════════════════════════════════════════════════════════════════

class YOLOv8SAHIAdapter(BaseModelAdapter):
    """
    Adaptador concreto para modelos YOLOv8 ejecutados mediante SAHI.

    Dependencias requeridas:
        pip install sahi ultralytics
    """

    MODEL_TYPE = "yolov8"

    def load(self) -> None:
        """Inicializa AutoDetectionModel de SAHI con el .pt indicado."""
        try:
            from sahi import AutoDetectionModel
        except ImportError as e:
            raise ImportError(
                "SAHI no está instalado. Ejecutá: pip install sahi ultralytics"
            ) from e

        print(f"[YOLOv8SAHIAdapter] Cargando modelo: {self.model_path} en {self.device}")
        self._model = AutoDetectionModel.from_pretrained(
            model_type=self.MODEL_TYPE,
            model_path=self.model_path,
            confidence_threshold=self.confidence,
            device=self.device,
        )
        print(f"[YOLOv8SAHIAdapter] Modelo listo.")

    def predict(
        self,
        image_path: str,
        slice_height: int = 512,
        slice_width: int = 512,
        overlap_height: float = 0.2,
        overlap_width: float = 0.2,
    ) -> PredictionResult:
        """Corre inferencia SAHI y empaqueta el resultado en PredictionResult."""
        self.ensure_loaded()

        try:
            from sahi.predict import get_sliced_prediction
        except ImportError as e:
            raise ImportError("SAHI no está instalado.") from e

        print(f"[YOLOv8SAHIAdapter] Procesando: {Path(image_path).name}")
        raw = get_sliced_prediction(
            image_path,
            self._model,
            slice_height=slice_height,
            slice_width=slice_width,
            overlap_height_ratio=overlap_height,
            overlap_width_ratio=overlap_width,
        )

        detections = [
            Detection(
                category=pred.category.name,
                score=pred.score.value,
                bbox=pred.bbox.to_xyxy(),
            )
            for pred in raw.object_prediction_list
        ]

        return PredictionResult(
            detections=detections,
            model_source="",        # ModelService lo completa
            model_name=Path(self.model_path).name,
            raw=raw,
        )


# ══════════════════════════════════════════════════════════════════════════════
# 4. Registro de adaptadores (extensibilidad futura)
# ══════════════════════════════════════════════════════════════════════════════

# Para agregar un nuevo tipo de modelo basta con registrarlo aquí.
# El ModelService lo instanciará automáticamente por clave.
MODEL_REGISTRY: dict[str, type[BaseModelAdapter]] = {
    "yolov8": YOLOv8SAHIAdapter,
    # "yolov9": YOLOv9SAHIAdapter,   # ejemplo de extensión futura
    # "rtdetr":  RTDETRAdapter,
}


# ══════════════════════════════════════════════════════════════════════════════
# 5. ModelService — capa de servicio (default vs. local)
# ══════════════════════════════════════════════════════════════════════════════

class ModelService:
    """
    Resuelve qué modelo usar (default del servidor o local subido por el usuario)
    y gestiona el ciclo de vida del adaptador activo.

    Uso típico desde Flask:
        service = ModelService(default_model_path="modelos/best.pt")
        result  = service.run(
            use_local=True,
            local_path="/tmp/uploads/mi_modelo.pt",
            image_path="/tmp/uploads/foto.JPG",
            confidence=0.3,
            device="cpu",
        )
    """

    def __init__(
        self,
        default_model_path: str,
        model_type: str = "yolov8",
        default_device: str = "cpu",
        default_confidence: float = 0.3,
    ):
        if model_type not in MODEL_REGISTRY:
            raise ValueError(
                f"Tipo de modelo '{model_type}' no registrado. "
                f"Opciones: {list(MODEL_REGISTRY.keys())}"
            )
        self._default_model_path = default_model_path
        self._model_type = model_type
        self._default_device = default_device
        self._default_confidence = default_confidence

        self._adapter: Optional[BaseModelAdapter] = None
        self._adapter_hash: Optional[str] = None

    # ── API pública ────────────────────────────────────────────────────────

    def run(
        self,
        image_path: str,
        use_local: bool = False,
        local_path: Optional[str] = None,
        confidence: Optional[float] = None,
        device: Optional[str] = None,
        slice_height: int = 512,
        slice_width: int = 512,
        overlap_height: float = 0.2,
        overlap_width: float = 0.2,
    ) -> PredictionResult:
        """
        Punto de entrada único para el controlador Flask.

        Args:
            use_local:  True  → usa `local_path` (subido por usuario).
                        False → usa el modelo default del servidor.
            local_path: Ruta al .pt local. Requerido si use_local=True.
        """
        # ── Resolver fuente ────────────────────────────────────────────────
        if use_local:
            if not local_path or not Path(local_path).exists():
                raise FileNotFoundError(
                    "Se seleccionó modo local pero no se encontró el archivo .pt."
                )
            resolved_path = local_path
            source_label  = "local"
        else:
            if not Path(self._default_model_path).exists():
                raise FileNotFoundError(
                    f"Modelo default no encontrado: {self._default_model_path}"
                )
            resolved_path = self._default_model_path
            source_label  = "default"

        conf   = confidence if confidence is not None else self._default_confidence
        dev    = device     if device     is not None else self._default_device

        # ── Obtener / reusar adaptador ─────────────────────────────────────
        adapter = self._get_adapter(resolved_path, conf, dev)

        # ── Inferencia ────────────────────────────────────────────────────
        result = adapter.predict(
            image_path=image_path,
            slice_height=slice_height,
            slice_width=slice_width,
            overlap_height=overlap_height,
            overlap_width=overlap_width,
        )

        result.model_source = source_label
        return result

    # ── Internos ───────────────────────────────────────────────────────────

    def _get_adapter(
        self, model_path: str, confidence: float, device: str
    ) -> BaseModelAdapter:
        """
        Devuelve el adaptador activo, recargándolo sólo si la config cambió.
        """
        AdapterClass = MODEL_REGISTRY[self._model_type]
        new_adapter  = AdapterClass(model_path, confidence, device)
        new_hash     = new_adapter._config_hash

        if self._adapter is None or self._adapter_hash != new_hash:
            self._adapter      = new_adapter
            self._adapter_hash = new_hash
            self._adapter.load()

        return self._adapter