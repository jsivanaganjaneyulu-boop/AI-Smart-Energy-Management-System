import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# -----------------------------
# Load YOLOv8 Model
# -----------------------------
model = YOLO("yolov8n.pt")

# -----------------------------
# Initialize DeepSORT Tracker
# -----------------------------
tracker = DeepSort(
    max_age=30,
    n_init=3,
    max_iou_distance=0.7
)

# -----------------------------
# Open Webcam
# -----------------------------
cap = cv2.VideoCapture(0)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # -----------------------------
    # Run YOLO Detection
    # -----------------------------
    results = model(frame, verbose=False)

    detections = []

    # -----------------------------
    # Extract Person Detections
    # -----------------------------
    for result in results:

        for box in result.boxes:

            cls = int(box.cls[0])

            # COCO Class 0 = Person
            if cls == 0:

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                confidence = float(box.conf[0])

                width = x2 - x1
                height = y2 - y1

                detections.append(
                    (
                        [x1, y1, width, height],
                        confidence,
                        "person"
                    )
                )

    # -----------------------------
    # Update DeepSORT
    # -----------------------------
    tracks = tracker.update_tracks(
        detections,
        frame=frame
    )

    person_count = 0

    # -----------------------------
    # Draw Tracking Results
    # -----------------------------
    for track in tracks:

        if not track.is_confirmed():
            continue

        person_count += 1

        track_id = track.track_id

        l, t, r, b = map(int, track.to_ltrb())

        # Bounding Box
        cv2.rectangle(
            frame,
            (l, t),
            (r, b),
            (0, 255, 0),
            2
        )

        # Person ID
        cv2.putText(
            frame,
            f"ID : {track_id}",
            (l, t - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

    # -----------------------------
    # Display Person Count
    # -----------------------------
    cv2.putText(
        frame,
        f"People : {person_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2
    )

    # -----------------------------
    # Room Status
    # -----------------------------
    if person_count == 0:
        status = "EMPTY"
        color = (0, 0, 255)
    else:
        status = "OCCUPIED"
        color = (0, 255, 0)

    cv2.putText(
        frame,
        f"Room : {status}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        2
    )

    # -----------------------------
    # Show Output
    # -----------------------------
    cv2.imshow("AI Smart Energy Tracker", frame)

    # Press Q to Exit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# -----------------------------
# Cleanup
# -----------------------------
cap.release()
cv2.destroyAllWindows()