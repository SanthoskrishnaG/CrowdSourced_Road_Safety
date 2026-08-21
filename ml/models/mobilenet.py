"""
MobileNetV3 Deep Learning Model Strategy for Road Infrastructure Classification.

Model Choice Rationale:
- Architecture: MobileNetV3-Small / MobileNetV3-Large
- Pretrained Base: ImageNet-1k
- Adaptation Strategy: Replace final linear classification head with a Dropout(0.2) + Linear(1024, 8) + Softmax
- Input Dimensions: (3, 224, 224) RGB, normalized with ImageNet mean/std
- Inference Speed: ~8-15ms on CPU, suitable for edge devices, citizen mobile uploads, and high-throughput servers.
"""

import json
from typing import Dict, List, Tuple, Optional
import numpy as np


class MobileNetConfig:
    INPUT_SIZE = (224, 224)
    NUM_CLASSES = 8
    MEAN = [0.485, 0.456, 0.406]
    STD = [0.229, 0.224, 0.225]
    ARCHITECTURE = "mobilenet_v3_small"
    MODEL_VERSION = "mobilenetv3-road-v1.0"


def get_pytorch_model_code() -> str:
    """
    Returns the exact PyTorch Transfer Learning code specification for fine-tuning MobileNetV3 on road hazards.
    """
    return '''
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

def build_mobilenet_road_classifier(num_classes: int = 8) -> nn.Module:
    weights = MobileNet_V3_Small_Weights.DEFAULT
    model = mobilenet_v3_small(weights=weights)
    
    # Freeze early feature extraction layers
    for param in model.features[:-2].parameters():
        param.requires_grad = False
        
    # Replace classifier head
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 1024),
        nn.Hardswish(),
        nn.Dropout(p=0.2),
        nn.Linear(1024, num_classes)
    )
    return model
'''
