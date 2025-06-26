from typing import Any, Optional, Union, Tuple, List, Dict
import sys
import json
from PIL import Image
import torchvision.transforms as transforms
import torchvision.models as models
import torch

_model = None
_labels = None


def _load_model_and_labels():
    global _model, _labels
    if _model is None:
        _model = models.resnet18(pretrained=True)
        _model.eval()
    if _labels is None:
        with open("classifier/imagenet-labels.json", "r") as f:
            _labels = json.load(f)


def classify(image_path: str) -> str:
    _load_model_and_labels()
    img = Image.open(image_path).convert("RGB")
    tensor = transforms.ToTensor()(img).unsqueeze(0)
    outputs = _model(tensor)
    _, pred = torch.max(outputs, 1)
    return _labels[int(pred.item())]


if __name__ == "__main__":
    path = sys.argv[1]
    label = classify(path)
    print(f"{path.split('/')[-1]},{label}")
