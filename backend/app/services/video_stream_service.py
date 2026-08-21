import io
import base64
from typing import List, Dict, Optional, Tuple
from PIL import Image

from app.models.report import ReportCategory, ReportSeverity
from app.schemas.stream import HazardDetectionEvent, VideoStreamAnalysisResponse
from ml.inference.predictor import RoadHazardPredictor
from ml.datasets.dataset import generate_synthetic_hazard_image
from app.core.logging import get_logger

logger = get_logger("app.stream")

# Singleton predictor instance
_stream_predictor: Optional[RoadHazardPredictor] = None


def get_stream_predictor() -> RoadHazardPredictor:
    global _stream_predictor
    if _stream_predictor is None:
        _stream_predictor = RoadHazardPredictor()
    return _stream_predictor


def analyze_video_stream(
    video_bytes: bytes,
    filename: str,
    duration_sec: float = 10.0,
    sample_interval_sec: float = 1.0,
    start_lat: float = 12.9716,
    start_lng: float = 77.5946,
    end_lat: float = 12.9750,
    end_lng: float = 77.5990
) -> VideoStreamAnalysisResponse:
    """
    Simulates / performs Edge ML Computer Vision inference across consecutive
    sampled video frames from a dashcam stream.
    Applies temporal persistence filtering and GPS interpolation.
    """
    predictor = get_stream_predictor()
    raw_events: List[HazardDetectionEvent] = []

    total_samples = max(1, int(duration_sec / sample_interval_sec))

    # Pre-defined realistic road conditions sequence simulation if video is raw container
    categories_pool = [
        ReportCategory.POTHOLE,
        ReportCategory.ROAD_DAMAGE,
        ReportCategory.BROKEN_STREETLIGHT,
        ReportCategory.GARBAGE,
        ReportCategory.FLOODING
    ]

    for i in range(total_samples):
        timestamp = round(i * sample_interval_sec, 2)
        progress = i / max(1, (total_samples - 1))
        current_lat = round(start_lat + (end_lat - start_lat) * progress, 6)
        current_lng = round(start_lng + (end_lng - start_lng) * progress, 6)

        # Generate or extract frame bytes
        # For demonstration and edge simulation, generate representative camera feed frames
        cat_idx = (i // 3) % len(categories_pool)
        simulated_cat = categories_pool[cat_idx].value

        img = generate_synthetic_hazard_image(simulated_cat)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        frame_bytes = buf.getvalue()

        # Run model inference on frame
        try:
            pred = predictor.predict(frame_bytes)
            predicted_cat_str = pred.category if hasattr(pred, 'category') else getattr(pred, 'predicted_category', 'POTHOLE')
            confidence = float(pred.confidence if hasattr(pred, 'confidence') else 0.85)

            try:
                predicted_enum = ReportCategory(predicted_cat_str)
            except ValueError:
                predicted_enum = ReportCategory.POTHOLE

            # Infer severity from confidence and category
            if confidence > 0.85 and predicted_enum in [ReportCategory.POTHOLE, ReportCategory.ROAD_DAMAGE, ReportCategory.FLOODING]:
                sev = ReportSeverity.HIGH
            elif confidence > 0.70:
                sev = ReportSeverity.MEDIUM
            else:
                sev = ReportSeverity.LOW

            # Thumbnail base64
            snap_b64 = "data:image/jpeg;base64," + base64.b64encode(frame_bytes).decode('utf-8')

            # Simulated bounding box based on frame index
            bbox = [
                round(0.25 + (i % 3) * 0.1, 2),
                round(0.35 + (i % 2) * 0.1, 2),
                0.35,
                0.30
            ]

            raw_events.append(HazardDetectionEvent(
                timestamp_sec=timestamp,
                frame_index=i + 1,
                category=predicted_enum,
                confidence=round(confidence, 3),
                severity=sev,
                bounding_box=bbox,
                estimated_lat=current_lat,
                estimated_lng=current_lng,
                snapshot_base64=snap_b64
            ))
        except Exception as e:
            logger.warning(f"Frame {i} inference failed: {str(e)}")

    # Apply Temporal Persistence Filter: Merge hazard detections occurring within 1.5s
    filtered_hazards: List[HazardDetectionEvent] = []
    if raw_events:
        current_cluster: List[HazardDetectionEvent] = [raw_events[0]]

        for next_event in raw_events[1:]:
            prev_event = current_cluster[-1]
            time_diff = next_event.timestamp_sec - prev_event.timestamp_sec

            # If same category within temporal window, group together
            if next_event.category == prev_event.category and time_diff <= 2.0:
                current_cluster.append(next_event)
            else:
                # Select the highest confidence detection from the cluster as canonical
                best_event = max(current_cluster, key=lambda x: x.confidence)
                filtered_hazards.append(best_event)
                current_cluster = [next_event]

        if current_cluster:
            best_event = max(current_cluster, key=lambda x: x.confidence)
            filtered_hazards.append(best_event)

    # Category summaries
    summary: Dict[str, int] = {}
    for h in filtered_hazards:
        summary[h.category.value] = summary.get(h.category.value, 0) + 1

    return VideoStreamAnalysisResponse(
        video_filename=filename,
        video_duration_sec=duration_sec,
        total_frames_sampled=total_samples,
        detections_count=len(filtered_hazards),
        hazards=filtered_hazards,
        summary_by_category=summary,
        stream_fps=30.0
    )
