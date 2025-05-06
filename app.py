from flask import Flask, render_template, request, Response, jsonify
import cv2
import numpy as np
import socket
import time
from tflite_runtime.interpreter import Interpreter
import MDD10A as HBridge
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import math
import os
import subprocess
import sys

# Initialize Flask app
app = Flask(__name__)

# User credentials
USERNAME = "admin"
PASSWORD = "password"

# Motor speed variables
speedleft = 0
speedright = 0

# Frame settings
FPS = 30
FRAME_DELAY = 1 / FPS
FRAME_WIDTH = 420
FRAME_HEIGHT = 240

# Gas detection settings
GAS_THRESHOLD = 1000  # PPM threshold
last_gas_reading = 0
gas_alert = False
raw_adc_value = 0  # Store raw ADC value for debugging

# Try to reset I2C bus using system commands
def reset_i2c_bus():
    print("Attempting to reset I2C bus...")
    try:
        # These commands might require sudo privileges
        os.system("sudo rmmod i2c_bcm2708 || true")
        os.system("sudo rmmod i2c_dev || true")
        time.sleep(1)
        os.system("sudo modprobe i2c_bcm2708")
        os.system("sudo modprobe i2c_dev")
        time.sleep(1)
    except Exception as e:
        print(f"Error resetting I2C bus: {e}")

# Initialize I2C connection with multiple retry attempts
def init_adc(max_attempts=3):
    global ads, gas_sensor
    
    # First, try to reset the I2C bus
    reset_i2c_bus()
    
    for attempt in range(max_attempts):
        try:
            print(f"Initializing ADC, attempt {attempt+1}/{max_attempts}")
            
            # Use the lowest possible frequency and explicit address
            i2c = busio.I2C(board.SCL, board.SDA, frequency=10000)  # Very low frequency
            time.sleep(1)  # Longer delay after initialization
            
            # Check if the I2C device is available using i2cdetect
            try:
                result = subprocess.run(['i2cdetect', '-y', '1'], 
                                      capture_output=True, text=True)
                print(f"I2C bus scan result:\n{result.stdout}")
            except Exception as e:
                print(f"Failed to scan I2C bus: {e}")
                
            # Try to initialize the ADC with explicit address
            ads = ADS.ADS1115(i2c, address=0x48)  
            
            # Configure for best reliability
            ads.gain = 1  # Set gain
            ads.mode = 0  # Continuous conversion mode
            ads.data_rate = 8  # Lowest data rate (8 SPS) for maximum reliability
            
            # Try to create the analog input
            gas_sensor = AnalogIn(ads, ADS.P0)
            
            # Validate by attempting a read operation
            test_value = gas_sensor.value
            test_voltage = gas_sensor.voltage
            print(f"ADC test read - Raw Value: {test_value}, Voltage: {test_voltage}V")
            
            print("ADC initialized successfully")
            return True
            
        except OSError as e:
            print(f"I2C OSError on attempt {attempt+1}: {e}")
            time.sleep(2)  # Wait before retrying
        except Exception as e:
            print(f"Unexpected error on attempt {attempt+1}: {e}")
            time.sleep(2)  # Wait before retrying
    
    print("Failed to initialize ADC after multiple attempts")
    return False

# Try to initialize the ADC
adc_available = init_adc(max_attempts=3)

# Alternative direct I2C implementation if the Adafruit library fails
# This is a fallback method that might work when the library doesn't
try:
    import smbus
    use_smbus_fallback = not adc_available
    if use_smbus_fallback:
        print("Trying alternative I2C implementation with smbus...")
        smbus_i2c = smbus.SMBus(1)  # 1 for Raspberry Pi 2 and later
        ADS1115_ADDRESS = 0x48
        ADS1115_REG_POINTER_CONVERT = 0x00
        ADS1115_REG_CONFIG = 0x01
        # Config for reading A0 with gain=1
        ADS1115_CONFIG = 0x8183  # Single-shot, A0, +/-4.096V, 8 SPS
except ImportError:
    print("smbus not available, skipping alternative implementation")
    use_smbus_fallback = False

def read_adc_with_smbus():
    try:
        # Write config register to start conversion
        msb = (ADS1115_CONFIG >> 8) & 0xFF
        lsb = ADS1115_CONFIG & 0xFF
        smbus_i2c.write_i2c_block_data(ADS1115_ADDRESS, ADS1115_REG_CONFIG, [msb, lsb])
        
        # Wait for conversion to complete
        time.sleep(0.2)
        
        # Read conversion register
        data = smbus_i2c.read_i2c_block_data(ADS1115_ADDRESS, ADS1115_REG_POINTER_CONVERT, 2)
        val = (data[0] << 8) | data[1]
        
        # Convert to voltage (4.096V reference / 32767)
        if val > 32767:
            val -= 65535
        voltage = val * 4.096 / 32767
        
        return val, voltage
    except Exception as e:
        print(f"SMBus read error: {e}")
        return 0, 0

# Simplified direct approach for MQ135
def calculate_ppm():
    global raw_adc_value, last_gas_reading, gas_alert
    
    if not adc_available and not use_smbus_fallback:
        return 0  # Return default value if ADC isn't available
    
    try:
        # Get the raw ADC value with error handling
        if adc_available:
            try:
                raw_adc_value = gas_sensor.value
                voltage = gas_sensor.voltage
            except Exception as e:
                print(f"Adafruit library read error: {e}")
                if use_smbus_fallback:
                    print("Falling back to SMBus implementation...")
                    raw_adc_value, voltage = read_adc_with_smbus()
                else:
                    return 0
        else:
            # Use SMBus implementation directly
            raw_adc_value, voltage = read_adc_with_smbus()
        
        last_gas_reading = voltage
        
        # Print debugging info to console
        print(f"Raw ADC: {raw_adc_value}, Voltage: {voltage}V")
        
        # Simple equation for estimating CO2 PPM based on voltage
        if voltage > 0:
            ppm = voltage * 700  # Simple scaling factor
        else:
            ppm = 0
        
        # Check if alert needed
        gas_alert = ppm > GAS_THRESHOLD
        
        # Return calculated PPM
        return ppm
    except OSError as e:
        print(f"ADC read error: {e}")
        return 0  # Return default value on error
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 0

# Load TFLite model
interpreter = Interpreter(model_path="crack_detection_model.tflite")
interpreter.allocate_tensors()

# Get model input/output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Initialize video capture
def gen_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # Try to read gas sensor
        ppm = calculate_ppm()

        # Preprocess frame for TFLite model
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (120, 120))
        normalized = resized.astype(np.float32) / 255.0
        input_data = np.expand_dims(normalized, axis=(0, -1))

        # Run inference
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        prediction = output_data[0][0]

        # Display result text on frame
        label = "Crack detected!" if prediction > 0.5 else "Detecting cracks..."
        color = (0, 0, 255) if prediction > 0.5 else (0, 255, 0)
        cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        # Display gas debugging info
        if adc_available or use_smbus_fallback:
            status = "Active" if ppm > 0 else "Error"
            cv2.putText(frame, f"Gas: {ppm:.1f} PPM ({status})", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(frame, f"Voltage: {last_gas_reading:.3f}V", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Raw ADC: {raw_adc_value}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            cv2.putText(frame, "Gas Sensor: Not Available", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Encode and yield frame
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        time.sleep(FRAME_DELAY)

    cap.release()

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            return render_template('stream.html', sensor_available=(adc_available or use_smbus_fallback))
        else:
            error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/gas_data')
def gas_data():
    if adc_available or use_smbus_fallback:
        ppm = calculate_ppm()
        return jsonify({
            'voltage': last_gas_reading,
            'ppm': ppm,
            'raw_adc': raw_adc_value,
            'alert': gas_alert,
            'available': ppm > 0  # Consider sensor available if we get a reading
        })
    else:
        return jsonify({
            'voltage': 0,
            'ppm': 0,
            'raw_adc': 0,
            'alert': False,
            'available': False
        })

@app.route('/reset_adc')
def reset_adc():
    global adc_available
    adc_available = init_adc(max_attempts=2)
    return jsonify({
        'success': adc_available,
        'message': "ADC reset successful" if adc_available else "ADC reset failed"
    })

@app.route('/<direction>')
def move(direction):
    global speedleft, speedright

    speeds = {
        "up": (0.02, -0.02),
        "down": (-0.02, 0.02),
        "stop": (0, 0),
        "right": (0.02, 0.02),
        "left": (-0.02, -0.02)
    }

    speedleft, speedright = speeds.get(direction, (0, 0))
    HBridge.setMotorLeft(speedleft)
    HBridge.setMotorRight(speedright)

    print(f"Command Received: {direction}")
    print(f"Command Sent to MDD10A.py - Left: {speedleft}, Right: {speedright}")

    return f"Key pressed: {direction}"

if __name__ == '__main__':
    # Test sensor reading before starting Flask app
    print("\n=== MQ135 SENSOR TEST ===")
    if adc_available:
        try:
            print(f"Raw ADC value: {gas_sensor.value}")
            print(f"Voltage: {gas_sensor.voltage:.3f}V")
        except Exception as e:
            print(f"Error reading sensor: {e}")
            print("Trying SMBus fallback...")
            if use_smbus_fallback:
                val, voltage = read_adc_with_smbus()
                print(f"SMBus read - Raw value: {val}, Voltage: {voltage}V")
                if val == 0 and voltage == 0:
                    print("SMBus fallback also failed")
            print("Continuing with gas sensor disabled")
            adc_available = False
    elif use_smbus_fallback:
        print("Trying SMBus implementation...")
        val, voltage = read_adc_with_smbus()
        print(f"SMBus read - Raw value: {val}, Voltage: {voltage}V")
    else:
        print("ADC not available - continuing without gas sensor")
    print("=========================\n")
    
    # Install smbus if not already installed (requires internet)
    if not adc_available and not use_smbus_fallback:
        print("Attempting to install smbus library...")
        os.system("pip install smbus")
        try:
            import smbus
            use_smbus_fallback = True
            print("SMBus installed successfully")
        except ImportError:
            print("Failed to install SMBus")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()

    print(f"Access the Web Rover at: http://{ip_address}:5000")
    app.run(host=ip_address, port=5000, debug=True)