import RPi.GPIO as io

# Use Broadcom pin numbering
io.setmode(io.BCM)
io.setwarnings(False)

# Constants
PWM_MAX = 100  # Maximum PWM value

# Motor control GPIO pins
leftMotor_DIR_pin = 22
rightMotor_DIR_pin = 23
leftMotor_PWM_pin = 17
rightMotor_PWM_pin = 18

# GPIO setup
io.setup(leftMotor_DIR_pin, io.OUT)
io.setup(rightMotor_DIR_pin, io.OUT)
io.setup(leftMotor_PWM_pin, io.OUT)
io.setup(rightMotor_PWM_pin, io.OUT)

# Set initial direction to False (neutral)
io.output(leftMotor_DIR_pin, False)
io.output(rightMotor_DIR_pin, False)

# Initialize PWM at 1kHz frequency
leftMotorPWM = io.PWM(leftMotor_PWM_pin, 1000)
rightMotorPWM = io.PWM(rightMotor_PWM_pin, 1000)

# Start PWM with 0% duty cycle
leftMotorPWM.start(0)
rightMotorPWM.start(0)

# Initial motor power
leftMotorPower = 0
rightMotorPower = 0

# Get current motor power levels
def getMotorPowers():
    return (leftMotorPower, rightMotorPower)

# Set power for the left motor
def setMotorLeft(power):
    global leftMotorPower
    io.output(leftMotor_DIR_pin, power > 0)
    pwm = min(abs(int(PWM_MAX * power)), PWM_MAX)
    leftMotorPower = pwm
    leftMotorPWM.ChangeDutyCycle(pwm)

# Set power for the right motor
def setMotorRight(power):
    global rightMotorPower
    io.output(rightMotor_DIR_pin, power < 0)  # Adjusted logic for right direction
    pwm = min(abs(int(PWM_MAX * power)), PWM_MAX)
    rightMotorPower = pwm
    rightMotorPWM.ChangeDutyCycle(pwm)

# Stop motors and clean up GPIO
def exit():
    io.output(leftMotor_DIR_pin, False)
    io.output(rightMotor_DIR_pin, False)
    io.cleanup()
