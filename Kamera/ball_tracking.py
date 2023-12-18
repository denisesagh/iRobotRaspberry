#importiere die notwendigen Pakete

from collections import deque
from imutils.video import VideoStream
import numpy as np
import argparse
import cv2
import imutils
import time


from irobot_edu_sdk.backend.bluetooth import Bluetooth
from irobot_edu_sdk.robots import event, hand_over, Color, Robot, Root, Create3

robot = Create3(Bluetooth())
ap = argparse.ArgumentParser()
punkte = []

#Überprüft die Koordinaten des Punktes und gibt die Richtung an, in die der Roboter fahren soll
async def updateRoboterRichtung(points,robot):

    print (points[0])

    if 600 < points[0] <= 800:
        print ("richtung auf rechts geändert")
        await robot.set_wheel_speeds(10, 5)

    elif points[0] > 800:
        print ("richtung auf scharf rechts geändert")
        await robot.set_wheel_speeds(15, 0)

    elif 200 < points[0] <= 400:
        print ("richtung auf links geändert")
        await robot.set_wheel_speeds(5, 10)

    elif points[0] < 200:
        print ("richtung auf scharf links geändert")
        await robot.set_wheel_speeds(0, 15)

    else:
        print ("richtung auf geradeaus geändert")
        await robot.set_wheel_speeds(10, 10)


async def camera(robot):
    while True:
        ap.add_argument("-v", "--video",
                        help="path to the (optional) video file")
        ap.add_argument("-b", "--buffer", type=int, default=64,
                        help="max buffer size")
        args = vars(ap.parse_args())


        pts = deque(maxlen=args["buffer"])
        # if a video path was not supplied, grab the reference
        # to the webcam

        # Wenn kein Videopath angegeben wurde,
        # wird die Webcam als Referenz genommen
        if not args.get("video", False):
            vs = VideoStream(src=0).start()
        else:
            vs = cv2.VideoCapture(args["video"])

        # warm-up zeit für die Kamera oder Video-Datei
        time.sleep(2.0)

        # Main-Loop
        while True:
            # Nimmt den aktuellen Frame auf
            frame = vs.read()
            # handle the frame from VideoCapture or VideoStream
            # Der Frame von VideoCapture oder VideoStream wird behandelt
            frame = frame[1] if args.get("video", False) else frame
            # Wenn kein Frame vorhanden ist, ist das Ende des Videos erreicht
            if frame is None:
                break

            # Skaliere den Frame auf eine Breite von 1000 Pixel
            frame = imutils.resize(frame, width=1000)

            # Konvertiere das Bild in den HSV-Farbraum
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Definiere den Farbbereich für Rot
            lower_red = np.array([0, 50, 50])
            upper_red = np.array([10, 255, 255])
            mask1 = cv2.inRange(hsv, lower_red, upper_red)

            lower_red = np.array([170, 50, 50])
            upper_red = np.array([180, 255, 255])
            mask2 = cv2.inRange(hsv, lower_red, upper_red)

            # Führe eine Bitwise-AND-Operation zwischen dem Maskenbild und dem ursprünglichen Bild aus
            mask = cv2.bitwise_or(mask1, mask2)
            res = cv2.bitwise_and(frame, frame, mask=mask)

            mask = cv2.erode(mask, None, iterations=2)
            mask = cv2.dilate(mask, None, iterations=2
                              )
            # Konturen werden erkannt
            cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
            cnts = imutils.grab_contours(cnts)
            center = None

            # Wenn die Kontur gefunden wurde, wird der Mittelpunkt berechnet
            if len(cnts) > 0:


                # Die stärkste Kontur wird gefunden und der Mittelpunkt wird berechnet
                c = max(cnts, key=cv2.contourArea)
                ((x, y), radius) = cv2.minEnclosingCircle(c)
                M = cv2.moments(c)
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                # Wenn der Radius größer als 10 ist, wird der Kreis und der Mittelpunkt auf dem Frame gezeichnet
                if radius > 10:

                    cv2.circle(frame, (int(x), int(y)), int(radius),
                               (0, 255, 255), 2)
                    cv2.circle(frame, center, 5, (0, 0, 255), -1)

            # Die Pointqueue wird aktualisiert
            pts.appendleft(center)

            # Die getracketen Punkte werden durchlaufen
            for i in range(1, len(pts)):
                # Wenn eines der Punkte None ist wird dieser übersprungen
                if pts[i - 1] is None or pts[i] is None:

                    continue
                # Sonst wird die Dicke der Linie berechnet und die Linie gezeichnet
                thickness = int(np.sqrt(args["buffer"] / float(i + 1)) * 2.5)
                cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)



                #updated die richtung des roboters 2x die Sekunde
                if time.time() % 0.5 < 0.1:
                    await updateRoboterRichtung(pts[i], robot)
                else:
                    break


            # Die verschiedenen Fenster werden angezeigt
            cv2.imshow('frame', frame)
            cv2.imshow('mask', mask)
            cv2.imshow('res', res)

            key = cv2.waitKey(1) & 0xFF

            # Wenn q gedrückt wird, wird die Schleife beendet
            if key == ord("q"):
                break

        # wenn kein Video angegeben wurde, wird die Webcam gestoppt
        if not args.get("video", False):
            vs.stop()

        # ansonsten wird das Video gestoppt
        else:
            vs.release()
        # close all windows
        cv2.destroyAllWindows()


#Funktion die erkennt wenn der Roboter auf ein Hindernis trifft
@event(robot.when_bumped, [True, True])
async def backoff(robot):
    await robot.set_lights_rgb(255, 80, 0)
    await robot.move(-20)
    await robot.turn_left(45)


# Funktion die gestartet werden muss, um den Roboter und die anderen Funktionen zu starten
@event(robot.when_play)
async def play(robot):
    await camera(robot)



robot.play()

