# Intelligent Duplicate Report Detection Architecture

## Overview
In a crowdsourced municipal reporting platform, multiple citizens often submit reports regarding the exact same physical road problem (e.g., a pothole on a busy intersection reported by 10 different commuters over a week).

The platform introduces a fundamental architectural separation:
- **`RoadReport`**: An individual submission from a citizen (containing their description, photo evidence, timestamp, and location).
- **`Issue`**: The canonical underlying road problem that authorities track, assign, prioritize, and resolve.

Multiple `RoadReport`s automatically merge into a single canonical `Issue`.

---

## Multi-Factor Duplicate Scoring Engine

When a new report is created, candidate active issues within a bounding box are evaluated using a deterministic composite similarity score $S_{\text{duplicate}} \in [0.0, 1.0]$:

$$S_{\text{duplicate}} = \frac{w_{\text{loc}} \cdot S_{\text{loc}} + w_{\text{cat}} \cdot S_{\text{cat}} + w_{\text{time}} \cdot S_{\text{time}} + w_{\text{img}} \cdot S_{\text{img}}}{w_{\text{loc}} + w_{\text{cat}} + w_{\text{time}} + w_{\text{img}}}$$

---

### 1. Geographic Distance Similarity ($S_{\text{loc}}$)
Uses the **Haversine formula** to calculate the great-circle distance $d$ in meters:
- $d \le 15.0\text{ m} \implies S_{\text{loc}} = 1.0$ (immediate vicinity)
- $15.0\text{ m} < d \le D_{\text{max}}\text{ (default 50.0 m)} \implies S_{\text{loc}} = 1.0 - \frac{d - 15.0}{D_{\text{max}} - 15.0}$
- $d > D_{\text{max}} \implies S_{\text{loc}} = 0.0$

### 2. Category Similarity ($S_{\text{cat}}$)
Evaluated via an explicit category taxonomy matrix:
- **Exact Match** ($1.0$): e.g., `POTHOLE` $\leftrightarrow$ `POTHOLE`
- **Related Categories** ($0.4 - 0.6$):
  - `POTHOLE` $\leftrightarrow$ `ROAD_DAMAGE` ($0.6$)
  - `BLOCKED_ROAD` $\leftrightarrow$ `OBSTRUCTION` ($0.6$)
  - `BLOCKED_ROAD` $\leftrightarrow$ `FLOODING` ($0.5$)
  - `DAMAGED_SIGN` $\leftrightarrow$ `ROAD_DAMAGE` ($0.4$)
- **Unrelated Categories** ($0.0$): e.g., `BROKEN_STREETLIGHT` $\leftrightarrow$ `FLOODING`

### 3. Time Proximity Decay ($S_{\text{time}}$)
Time difference $\Delta t = |t_{\text{new}} - t_{\text{issue}}|$:
- $\Delta t \le 24\text{ hours} \implies S_{\text{time}} = 1.0$
- $\Delta t \le 7\text{ days} \implies S_{\text{time}} = 0.8$
- $\Delta t \le 30\text{ days} \implies S_{\text{time}} = 0.4$
- $\Delta t > 30\text{ days} \implies S_{\text{time}} = 0.1$

### 4. Perceptual Image Hashing ($S_{\text{img}}$)
Uses **Difference Hashing (dHash)** with Pillow:
1. Resize image to $9 \times 8$ grayscale.
2. Calculate horizontal pixel gradient differences: $\text{diff}[x, y] = (\text{pixel}[x, y] > \text{pixel}[x+1, y])$.
3. Generate a 64-bit integer perceptual fingerprint.
4. Compare hashes using **Hamming Distance** $H \in [0, 64]$:
   $$S_{\text{img}} = \max\left(0.0, 1.0 - \frac{H}{64}\right)$$

> [!NOTE]
> **Limitations**: Perceptual dHash captures structural luminance gradients. It is resilient against resizing, minor cropping, and compression, but is not deep-learning object understanding. When neither report has images, $w_{\text{img}}$ is dynamically redistributed among location, category, and time factors.

---

## Configuration Defaults

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `DUPLICATE_SCORE_THRESHOLD` | `0.65` | Minimum composite score required to merge reports into an existing Issue |
| `DUPLICATE_DISTANCE_THRESHOLD_METERS` | `50.0` | Maximum physical search radius for duplicate candidates |
| `WEIGHT_LOCATION` | `0.40` | Weight assigned to geographic proximity |
| `WEIGHT_CATEGORY` | `0.30` | Weight assigned to problem category match |
| `WEIGHT_TIME` | `0.15` | Weight assigned to report recency |
| `WEIGHT_IMAGE` | `0.15` | Weight assigned to perceptual image similarity |
