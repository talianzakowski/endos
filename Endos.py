import sys
import cv2
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QSlider,
)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt


class CameraWidget(QWidget):
    def __init__(self, camera_index=0):
        super().__init__()
        self.setWindowTitle("Endoscope Viewer")
        self.label = QLabel()
        self.label.setFixedSize(640, 480)

        # Buttons
        self.capture_btn = QPushButton("Capture Image")
        self.record_btn = QPushButton("Start Recording")
        self.freeze_btn = QPushButton("Freeze Frame")
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(1)
        self.zoom_slider.setMaximum(4)
        self.zoom_slider.setValue(1)
        self.zoom_slider.setTickInterval(1)
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setMinimum(-100)
        self.brightness_slider.setMaximum(100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.setTickInterval(10)
        self.brightness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.capture_btn)
        btn_layout.addWidget(self.record_btn)
        btn_layout.addWidget(self.freeze_btn)
        btn_layout.addWidget(QLabel("Zoom"))
        btn_layout.addWidget(self.zoom_slider)
        btn_layout.addWidget(QLabel("Brightness"))
        btn_layout.addWidget(self.brightness_slider)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.cap = cv2.VideoCapture(camera_index)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~30 fps

        self.is_frozen = False
        self.last_frame = None
        self.is_recording = False
        self.video_writer = None
        self.record_btn.clicked.connect(self.toggle_recording)
        self.capture_btn.clicked.connect(self.capture_image)
        self.freeze_btn.clicked.connect(self.toggle_freeze)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        self.brightness_slider.valueChanged.connect(self.update_brightness)
        self.zoom_factor = 1
        self.brightness = 0

    def update_frame(self):
        if self.is_frozen and self.last_frame is not None:
            frame = self.last_frame
        else:
            ret, frame = self.cap.read()
            if not ret:
                return
            self.last_frame = frame.copy()

        # Apply zoom
        frame = self.apply_zoom(frame)
        # Apply brightness
        frame = self.apply_brightness(frame)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(
            rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        )
        self.label.setPixmap(QPixmap.fromImage(qt_image))

        # Recording
        if self.is_recording:
            if self.video_writer is None:
                fourcc = cv2.VideoWriter.fourcc(*"mp4v")
                out_path = QFileDialog.getSaveFileName(
                    self, "Save Video", "", "MP4 Files (*.mp4)"
                )[0]
                if out_path:
                    self.video_writer = cv2.VideoWriter(
                        out_path, fourcc, 30, (frame.shape[1], frame.shape[0])
                    )
                else:
                    self.is_recording = False
                    self.record_btn.setText("Start Recording")
                    return
            self.video_writer.write(frame)

    def capture_image(self):
        if self.last_frame is not None:
            out_path = QFileDialog.getSaveFileName(
                self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpg)"
            )[0]
            if out_path:
                cv2.imwrite(out_path, self.last_frame)

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_btn.setText("Stop Recording")
            self.video_writer = None
        else:
            self.is_recording = False
            self.record_btn.setText("Start Recording")
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

    def toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        self.freeze_btn.setText("Unfreeze" if self.is_frozen else "Freeze Frame")

    def update_zoom(self, value):
        self.zoom_factor = value

    def apply_zoom(self, frame):
        if self.zoom_factor > 1:
            h, w = frame.shape[:2]
            nh, nw = h // self.zoom_factor, w // self.zoom_factor
            y1 = (h - nh) // 2
            x1 = (w - nw) // 2
            cropped = frame[y1 : y1 + nh, x1 : x1 + nw]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
        return frame

    def update_brightness(self, value):
        self.brightness = value

    def apply_brightness(self, frame):
        if self.brightness != 0:
            frame = cv2.convertScaleAbs(frame, alpha=1, beta=self.brightness)
        return frame

    def closeEvent(self, event):
        self.cap.release()
        if self.video_writer:
            self.video_writer.release()
        event.accept()


def main():
    app = QApplication(sys.argv)
    widget = CameraWidget()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
