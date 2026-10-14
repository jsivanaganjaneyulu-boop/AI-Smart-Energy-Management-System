import cv2
from ultralytics import YOLO

# Check OpenCV version
print("OpenCV Version:", cv2.__version__)

# Load YOLOv8 model
model = YOLO("yolov8n.pt")

# Open the camera
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Check whether the camera opened successfully
if not cap.isOpened():
    print("Camera could not be opened.")
    exit()

print("Camera started successfully.")
print("Press Q to quit.")

while True:

    # Read frame from camera
    ret, frame = cap.read()

    if not ret:
        print("Frame not received.")
        break

    # Run YOLO detection
    results = model(frame, verbose=False)

    # Initialize person count
    person_count = 0

    # Process detection results
    for result in results:

        boxes = result.boxes

        for box in boxes:

            # Get class ID
            cls = int(box.cls[0])

            # Person class ID in COCO dataset = 0
            if cls == 0:

                person_count += 1

                # Get bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # Get confidence
                confidence = float(box.conf[0])

                # Draw bounding box
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                # Display confidence
                cv2.putText(
                    frame,
                    f"Person {confidence:.2f}",
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2
                )

    # Display people count
    cv2.putText(
        frame,
        f"People Count: {person_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2
    )

    # Determine room status
    if person_count == 0:
        status = "ROOM EMPTY - LIGHT OFF"
        color = (0, 0, 255)
    else:
        status = "ROOM OCCUPIED - LIGHT ON"
        color = (0, 255, 0)

    # Display room status
    cv2.putText(
        frame,
        status,
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2
    )

    # Display video
    cv2.imshow(
        "AI Smart Energy Management System",
        frame
    )

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Release camera
cap.release()

# Close all OpenCV windows
cv2.destroyAllWindows()

print("System stopped.")