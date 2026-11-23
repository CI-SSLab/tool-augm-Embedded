"""Image encoder: EmbeddingGemma 2 by default, swappable through IMAGE_ENCODER."""
import os

import numpy as np
import torch
from PIL import Image, ImageOps
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL = "google/embeddinggemma-2"
DEFAULT_BUDGET = 280  # image soft tokens: 70 / 140 / 280 / 560 / 1120


def _dtype(device: str):
    # bf16 only where the hardware has it (Ampere+). Never fp16: it overflows to NaN.
    if device.startswith("cuda") and torch.cuda.get_device_capability(torch.device(device))[0] >= 8:
        return torch.bfloat16
    return torch.float32


def load_image(path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


class Encoder:
    def __init__(self, model: str = None, device: str = None, budget: int = DEFAULT_BUDGET):
        self.model_name = model or os.getenv("IMAGE_ENCODER") or DEFAULT_MODEL
        self.device = device or os.getenv("EMBED_DEVICE") or ("cuda:0" if torch.cuda.is_available() else "cpu")
        self.budget = budget
        self.model = SentenceTransformer(self.model_name, device=self.device,
                                         model_kwargs={"torch_dtype": _dtype(self.device)},
                                         config_kwargs={"audio_config": None})

    @property
    def slug(self) -> str:
        return f"{self.model_name.split('/')[-1]}_b{self.budget}"

    def embed(self, images: list, batch_size: int = 8) -> np.ndarray:
        """L2-normalised float32 embeddings, shape (len(images), dim)."""
        emb = self.model.encode([{"image": im} for im in images], batch_size=batch_size,
                                processing_kwargs={"image": {"max_soft_tokens": self.budget}},
                                convert_to_numpy=True, show_progress_bar=False)
        emb = emb.astype(np.float32)
        # Re-normalise in fp32: the bf16 forward pass leaves norms around 0.999
        return emb / np.linalg.norm(emb, axis=1, keepdims=True)
