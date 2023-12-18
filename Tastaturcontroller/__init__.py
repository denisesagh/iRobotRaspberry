import multiprocessing
from multiprocessing import Process
import keyboard
from irobot_edu_sdk.backend.bluetooth import Bluetooth
from irobot_edu_sdk.robots import event, Create3


robot = Create3(Bluetooth())
th = 150


# Funktion, die die Tastatureingaben abfragt und den Roboter steuert
@event(robot.when_play)
async def navigate(robot):
    while True:
        event = keyboard.read_event()
        key = event.name
        if key == 'w':
            await robot.set_wheel_speeds(70, 70)
            print("forward")
        elif key == 's':
            await robot.set_wheel_speeds(-70, -70)
            print("backward")
        elif key == 'a':
            await robot.set_wheel_speeds(10, 20)
            print("left")
        elif key == 'd':
            await robot.set_wheel_speeds(20, 10)
            print("right")
        elif key == 'q':
            await robot.turn_left(90)
            print("left")
        elif key == 'e':
            await robot.turn_right(90)
            print("right")
        elif key == 'space':
            await robot.stop()
            print("stop")
        else:
            pass


# Funktion die den Sensorwert abfragt und mit dem Schwellwert vergleicht
def front_obstacle(sensors):
    print(sensors[3])
    return sensors[3] > th


# Funktion die den Roboter zuück fährt, um 45 Grad dreht und die Farbe auf Rot setzt
async def backoff(robot):
    await robot.set_lights_rgb(255, 80, 0)
    await robot.move(-20)
    await robot.turn_left(45)

@event(robot.when_play)

async def play(robot):
    while True:
        # Sensor wird definiert, indem die Sensoren des Roboters abgefragt werden
        sensors = (await robot.get_ir_proximity()).sensors
        # Wenn der Sensor einen Wert über 150 hat, dann wird die Funktion backoff ausgeführt
        if front_obstacle(sensors):
            await backoff(robot)




robot.play()
