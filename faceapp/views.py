import base64
import re
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os
import face_recognition
import datetime
import json
import numpy as np
import cv2
def home(request):
    return render(request, 'home.html')


@csrf_exempt
def take_attendance(request):
    if request.method == "POST":
        try:
            import json, base64, re, datetime, os, face_recognition, cv2, numpy as np

            data = json.loads(request.body)
            image_data = data.get("image")
            if not image_data:
                return JsonResponse({"error": "No image received"}, status=400)

            # decode image
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # detect faces
            face_locations = face_recognition.face_locations(rgb_frame)

            if not face_locations:
                return JsonResponse({"message": "No face detected", "faces": []})

            # Prepare face rectangles for JS: [top, right, bottom, left]
            faces_for_js = [{"top": f[0], "right": f[1], "bottom": f[2], "left": f[3]} for f in face_locations]

            # Face recognition part (optional)
            students_dir = os.path.join(settings.BASE_DIR, "students")
            student_encodings = []
            student_names = []

            for file in os.listdir(students_dir):
                if file.endswith(".jpg") or file.endswith(".png"):
                    img = face_recognition.load_image_file(os.path.join(students_dir, file))
                    enc = face_recognition.face_encodings(img)
                    if enc:
                        student_encodings.append(enc[0])
                        student_names.append(file.rsplit(".", 1)[0])

            recognized = []
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(student_encodings, face_encoding)
                if True in matches:
                    match_index = matches.index(True)
                    name = student_names[match_index]
                    recognized.append(name)

                    # log attendance
                    now = datetime.datetime.now()
                    time_str = now.strftime("%H:%M:%S")
                    date_str = now.strftime("%Y-%m-%d")
                    log_path = os.path.join(settings.BASE_DIR, "attendance.csv")
                    with open(log_path, "a") as f:
                        f.write(f"{name},{time_str},{date_str}\n")

            return JsonResponse({"message": f"Attendance taken: {', '.join(recognized) if recognized else 'No match'}",
                                 "faces": faces_for_js})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"message": "Use POST request."})

@csrf_exempt
def add_student(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            student_name = data.get("name")

            if not student_name:
                return JsonResponse({"error": "No name provided"}, status=400)
            if not image_data:
                return JsonResponse({"error": "No image provided"}, status=400)

            # Decode base64 image
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)

            # Convert to OpenCV image
            import numpy as np
            import cv2
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect face
            import face_recognition
            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return JsonResponse({"message": "No face detected. Student not added."})

            # Only save image if face detected
            students_dir = os.path.join(settings.BASE_DIR, "students")
            os.makedirs(students_dir, exist_ok=True)
            save_path = os.path.join(students_dir, f"{student_name}.jpg")
            with open(save_path, "wb") as f:
                f.write(img_bytes)

            return JsonResponse({"message": f"Student {student_name} added successfully."})

        except Exception as e:
            print("ERROR in add_student:", e)
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, "add_student.html")

@csrf_exempt
def detect_faces(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            if not image_data:
                return JsonResponse({"faces": []})

            # Decode base64 image
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = frame[:, :, ::-1]  # BGR -> RGB

            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            faces_list = []
            for top, right, bottom, left in face_locations:
                faces_list.append({"top": top, "right": right, "bottom": bottom, "left": left})

            return JsonResponse({"faces": faces_list})
        except Exception as e:
            return JsonResponse({"error": str(e), "faces": []})
    return JsonResponse({"faces": []})

def view_records(request):
    
    return render(request, 'records.html',)