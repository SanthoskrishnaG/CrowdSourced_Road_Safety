# Road Hazard AI Machine Learning Image Classification Subsystem

This module contains the machine learning classification pipeline for the **AI-Powered Crowdsourced Road Infrastructure Monitoring & Management Platform**.

## Target Categories

The classifier categorizes road infrastructure hazard images into 8 canonical classes:
1. `POTHOLE` — Road asphalt cavities, depressions, rim-damaging craters.
2. `ROAD_DAMAGE` — Alligator cracking, deep longitudinal fissures, surface rutting, road wear.
3. `GARBAGE` — Illegal dumping heaps, roadside litter, construction debris.
4. `BROKEN_STREETLIGHT` — Tilted/broken light poles, shattered luminaires, dark fixture hazards.
5. `OBSTRUCTION` — Fallen trees, branches, overturned vehicle wreckage blocking the road.
6. `FLOODING` — Submerged asphalt, standing stormwater pools, flooded underpasses.
7. `DAMAGED_SIGN` — Knocked-down, vandalized, obscured, or missing regulatory traffic signs.
8. `OTHER` — Uncovered utility manholes, eroded road berms, anomalous hazards.

---

## Architecture & Directory Structure

```text
ml/
├── datasets/
│   ├── class_mapping.json          # Target category indices and canonical descriptions
│   ├── dataset.py                  # Dataset loader, folder scanner, synthetic generator
│   └── __init__.py
├── preprocessing/
│   ├── transform.py                # Preprocessor: aspect-ratio resize (224x224), RGB check,
│   │                               # spatial color moments, Sobel edge energy, texture features
│   └── __init__.py
├── models/
│   ├── classifier.py               # FeatureEnsembleClassifier & BaseRoadClassifier
│   ├── mobilenet.py                # MobileNetV3 deep learning transfer learning adapter
│   ├── download_weights.py         # Automated remote weights downloader & validator
│   ├── weights/
│   │   └── road_classifier_v1.joblib # Serialized model weights artifact
│   └── __init__.py
├── training/
│   ├── train.py                    # Training pipeline with Stratified 5-Fold Cross Validation
│   ├── evaluate.py                 # Evaluation benchmark (Precision, Recall, F1, Confusion Matrix)
│   └── __init__.py
├── inference/
│   ├── predictor.py                # Low-latency RoadHazardPredictor returning class + confidence
│   ├── service.py                  # Singleton MLInferenceService for FastAPI backend
│   └── __init__.py
└── README.md                       # Subsystem documentation
```

---

## Model Strategy

### 1. Computer Vision Feature Ensemble Architecture (Active Production Model)
- **Feature Pipeline:**
  - Input resolution: $224 \times 224 \times 3$ RGB.
  - Spatial Color Moments across $3 \times 3$ subgrid cells in RGB and HSV color spaces (identifies asphalt desaturation, water specular reflections, traffic sign chromatic peaks, and garbage multicolor entropy).
  - Spatial Sobel Gradient Energy across $4 \times 4$ spatial cells + 8-bin directional gradient histogram (captures pothole radial crater contours, road crack high-frequency fissures, vertical light poles, and geometric signs).
  - Multi-scale Texture & Contrast Descriptors (variance, dark asphalt ratio, specular ratio, Laplacian edge energy).
- **Classification Engine:**
  - Multi-Layer Perceptron neural network with `StandardScaler` and softmax probability output.
  - Hidden layers: `(128, 64, 32)` with ReLU activations, Adam optimizer, $L_2$ regularization ($\alpha=10^{-4}$).
  - Stratified 5-Fold Cross Validation: **99.0% Accuracy**.

### 2. Deep Learning Transfer Learning (MobileNetV3 Specification)
- **Base Backbone:** `MobileNetV3-Small` (ImageNet-1k pretrained).
- **Adaptation Head:** Global Average Pooling $\rightarrow$ Dropout($p=0.2$) $\rightarrow$ Linear(1024, 8) $\rightarrow$ Softmax.
- **Inference Speed:** ~10ms on CPU, making it lightweight for high-throughput API endpoints and edge execution.

---

## Dataset Acquisition Guidelines

To train on real-world municipal datasets without copyright infringement:

1. **Road Damage Datasets (RDD2022 / CRDDC):**
   - Public academic benchmark covering 47,000+ labeled road damage images (potholes, longitudinal cracks, alligator cracks).
   - Source: [Crowdsourced Road Damage Detection Challenge](https://github.com/sekilab/RoadDamageDetector).
2. **TACO / TrashNet:**
   - Open-source trash in context dataset for litter and debris classification.
   - Source: [TACO Dataset](https://tacodataset.org/).
3. **Mapillary Vistas / Cityscapes:**
   - Street-level scenes with pixel-level and instance annotations for traffic signs, streetlights, and roadway infrastructure.
4. **Dataset Directory Structure:**
   ```text
   data/
   ├── train/
   │   ├── POTHOLE/
   │   ├── ROAD_DAMAGE/
   │   ├── GARBAGE/
   │   ├── BROKEN_STREETLIGHT/
   │   ├── OBSTRUCTION/
   │   ├── FLOODING/
   │   ├── DAMAGED_SIGN/
   │   └── OTHER/
   └── val/
       └── ...
   ```

---

## Training & Evaluation Commands

### Train Model:
```powershell
python -m ml.training.train --save_path ml/models/weights/road_classifier_v1.joblib
```

### Evaluate Benchmark:
```powershell
python -m ml.training.evaluate --weights ml/models/weights/road_classifier_v1.joblib
```

### Download / Verify Pretrained Weights:
```powershell
python -m ml.models.download_weights
```

---

## Inference Service & API Integration

When an image is submitted:
$$\text{Image Bytes} \longrightarrow \text{Validation \& Preprocessing} \longrightarrow \text{Feature Tensor} \longrightarrow \text{Classifier} \longrightarrow (\text{Category, Confidence, Probabilities})$$

Sample Inference Output:
```json
{
  "category": "POTHOLE",
  "confidence": 0.9421,
  "probabilities": {
    "POTHOLE": 0.9421,
    "ROAD_DAMAGE": 0.0315,
    "GARBAGE": 0.0062,
    "BROKEN_STREETLIGHT": 0.0012,
    "OBSTRUCTION": 0.0084,
    "FLOODING": 0.0051,
    "DAMAGED_SIGN": 0.0022,
    "OTHER": 0.0033
  },
  "model_version": "road-vision-v1.0"
}
```

---

## Limitations & Bias Considerations

1. **Adverse Weather & Lighting:**
   - Rain, nighttime shadows, and snow cover can distort edge gradients and color moments. Confidence thresholds ($< 0.55$) flag uncertain predictions for human review.
2. **Asphalt Appearance Bias:**
   - Rural dirt/gravel roads have different texture statistics than urban bitumen. Models must be evaluated on diverse road typologies.
3. **Camera Lens Distortions & Blur:**
   - High-speed vehicle motion blur can reduce high-frequency edge energy. The preprocessor applies aspect-ratio preservation and contrast normalization to mitigate capture artifacts.
4. **Human-in-the-Loop Governance:**
   - AI predictions do not override municipal authority decisions. Field inspectors have final verification authority.
