
<h1 align="center">🤖 Industrial Web Rover</h1>
<h3 align="center">Real-Time Remote Inspection, Gas Sensing & AI-Based Crack Detection</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/OpenCV-27338e?style=for-the-badge&logo=opencv&logoColor=white"/>
  <img src="https://img.shields.io/badge/TensorFlow_Lite-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white"/>
  <img src="https://img.shields.io/badge/Raspberry_Pi-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white"/>
</p>

---

## 📌 Project Overview

The **Industrial Web Rover** is a Raspberry Pi-powered robotic platform designed for real-time monitoring in hazardous environments. It supports:
- 🎥 Live video streaming
- ⚙️ Remote motor control
- 🌫️ Gas detection using MQ135 sensor
- 🧠 AI-based crack detection using TensorFlow Lite

---

## 💡 Features

- 🔐 Secure login access
- 🖥️ Real-time camera feed with OpenCV
- 🎮 Web-based rover control using Flask + GPIO
- 🧪 Sensor dashboard with gas level and voltage display
- 📷 CNN-based crack detection deployed using TFLite
- 📊 Academic report and notebooks for documentation

---

## 📁 Project Files

| File                | Purpose                                               |
|---------------------|-------------------------------------------------------|
| `app.py`            | Main Flask server handling video, control, sensors    |
| `MDD10A.py`         | Motor driver interface for GPIO                       |
| `login.html`        | Login page for access control                         |
| `stream.html`       | Main UI for stream, control, and sensor data          |
| `Robotics_1_NO MATHS.ipynb` | Introductory notebook without math            |
| `Robotics_2_MATHS.ipynb`    | Notebook covering CNN, math, training         |
| `REPORT_ROBOTICS.pdf`       | Final project report with design & results     |

---

## 🔧 Technology Stack

- 🐍 Python, Flask, HTML/CSS
- 📸 OpenCV for video stream
- 🧠 TensorFlow Lite for AI inference
- ⚙️ Raspberry Pi GPIO for motor control
- 🌐 Web interface for real-time monitoring
- 📊 ADS1115 + MQ135 for gas level detection

---

## 🚀 How to Run

1. Connect camera, motor driver (MDD10A), and MQ135 gas sensor to Raspberry Pi
2. Run the server:
```bash
python3 app.py
```
3. Open browser: `http://<raspberry_pi_ip>:5000`
4. Log in and operate the rover remotely

---

## 📬 Contact

📧 Email: [Hariai.td@gmail.com](mailto:Hariai.td@gmail.com)  
🏫 Project by Hari Vaarthan T D — Amrita School of Artificial Intelligence

<p align="center">
  <img src="https://media.giphy.com/media/Q7ozWVYCR0nyW2ryxB/giphy.gif" width="200"/>
</p>
