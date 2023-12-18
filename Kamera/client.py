# Importiere die notwendigen Bibliotheken.
import socket
import struct
from collections import deque

import numpy as np

import cv2

# Erster Integer: 
#   0: Verbindung abbrechen; keine Bilder mehr vom Server.
#   1: Verbindung fortsetzen; es liegen noch Bilder im Server vor.
# Zweiter Integer: Größe des Frames in Bytes, das darauf folgt. 
unpacker = struct.Struct("<I I")

# HSV Farbreichweite für den Ball. 
lower_limit_hsv = (100, 60, 30)
upper_limit_hsv = (130, 255, 255)

# Anzahl an Punkten, die zum Zeichnen des Pfades verwendet werden. 
buffer = 128
pts = deque(maxlen=buffer)

# Verbinde mit dem Server.
server_address = ("localhost", 10000)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect(server_address)

    cv2.namedWindow("video", cv2.WINDOW_NORMAL)
    # Während der Server noch Bilder liefert, werden diese roh empfangen, 
    # und lokal bearbeitet, um den Raspberry Pi zu schonen. 
    # Alternativ kann der Nutzer hier über das Schließen des Fensters
    # die Verbindung schließen. 
    while True:
        # Empfange zunächst den Header, und dann das aktuelle Bild. 
        cont, size = unpacker.unpack(sock.recv(unpacker.size))
        if cont == 0: 
            break 
        frame = bytearray()
        while True:
            frame_part = sock.recv(size - len(frame))
            if not frame_part:
                break
            frame.extend(frame_part)

        # Wandele das Bild von den rohen Bytes in das cv2 Bildformat um. 
        frame_np = np.frombuffer(frame, np.uint8)
        frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)
        # frame = frame.reshape(shape)

        # Maskiere das Bild mit der oben definierten
        # Farbreichweite. 
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        frame_HSV = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(frame_HSV, lower_limit_hsv, upper_limit_hsv)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # Suche alle Konturen in der Maske. 
        contours, hierarchy = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Finde den besten "Ball", falls mehrere Objekte mit der richtigen
        # Farbe erkannt werden.
        best_contour = None
        for cnt in contours:
            approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
            n_approx = len(approx)
            if n_approx > 8:
                best_contour = cnt
                best_contour_area = cv2.contourArea(cnt)
                break

        if best_contour is not None:
            ((x, y), radius) = cv2.minEnclosingCircle(best_contour)            
            # Falls der Flächeninhalt des minEnclosingCircle nicht zumindest 
            # ungefähr mir dem Flächeninhalt der Kontur übereinstimmt, wird
            # davon ausgegangen, dass es sich doch nicht um einen Kreis (Ball)
            # handelt.  
            radius_area = 3.1415926535 * radius ** 2
            ratio = abs(best_contour_area - radius_area)/max(best_contour_area, radius_area)
            #print(best_contour_area, radius_area, ratio)
            if ratio < 0.25:
                M = cv2.moments(best_contour)
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                if radius > 1:
                    cv2.circle(frame, (int(x), int(y)), int(radius),
                            (0, 255, 255), 2)
                pts.appendleft(center)
        else:
            # Falls kein neuer Punkt für die Liste gefunden wurde, soll 
            # dennoch der älteste entfernt werden. 
            if len(pts) > 0:
                pts.pop()

        # Zeichne die Linie. 
        for i in range(1, len(pts)):
            if pts[i - 1] is None or pts[i] is None:
                continue
            cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), 2)

        # Auskommentieren, wenn nur die Maske (bzw. das Video unter der
        # Maske angezeigt werden soll).
        # frame = cv2.bitwise_and(frame, frame, mask=mask)

        cv2.imshow("video", frame)
        cv2.waitKey(1) # Wert anpassen, falls Video zu schnell ist. 

        # Prüfe, ob das "X" gedrückt wurde, falls ja, stoppe. 
        window_closed = False 
        try:
            cv2.getWindowProperty("video", 0)
        except cv2.error:
            window_closed = True 
        if not window_closed:
            sock.sendall(b"\xbe\xef")
        else:
            sock.sendall(b"\xaf\xfe")
            break
