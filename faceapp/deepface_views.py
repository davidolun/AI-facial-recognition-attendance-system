"""
DeepFace Face Recognition Implementation
=====================================

BEST OPTION FOR FREE HOSTING:
- Uses DeepFace with Facenet model (small, fast, accurate)
- No dlib required (avoids RAM issues during build)
- Works great on Render/Railway free tiers
"""

import numpy as np
import cv2
from PIL import Image
import io
import base64
import re
import json
import os
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Student, AttendanceSession, AttendanceRecord, Class
import cloudinary
import cloudinary.uploader

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'duu7pc7s3'),
    api_key=os.getenv('CLOUDINARY_API_KEY', '625655631397579'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET', 'HEE8Or7rvr7SBOv61t5CWsSRUIs')
)

# Try to import DeepFace
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    print("✅ DeepFace successfully imported!")
    
    # Configure DeepFace to use OpenCV backend (no TensorFlow required)
    import os
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow warnings
    
except ImportError as e:
    DEEPFACE_AVAILABLE = False
    print(f"Warning: DeepFace not available: {e}")
    print("Face recognition will be disabled.")
except Exception as e:
    DEEPFACE_AVAILABLE = False
    print(f"Warning: DeepFace import error: {e}")
    print("Face recognition will be disabled.")

# ========================================
# CORE FACE RECOGNITION FUNCTIONS
# ========================================

def extract_face_embedding_deepface(image_array, enforce_detection=True):
    """
    Extract face embedding using DeepFace (Facenet model)
    
    Args:
        image_array: numpy array of image (RGB)
        enforce_detection: If True, raises error if no face detected
    
    Returns:
        embedding: 128-dimensional face embedding (numpy array) or None
    """
    if not DEEPFACE_AVAILABLE:
        return None
        
    try:
        # Use Facenet model (small, fast, accurate)
        # Other options: VGG-Face, Facenet512, ArcFace
        embedding_objs = DeepFace.represent(
            img_path=image_array,
            model_name="Facenet",  # 22MB model - lightweight!
            detector_backend="opencv",  # Fast detector
            enforce_detection=enforce_detection,
            align=False  # Skip alignment for faster processing
        )
        
        if not embedding_objs:
            return None
        
        # Get the first face embedding
        embedding = np.array(embedding_objs[0]["embedding"])
        
        return embedding
        
    except Exception as e:
        print(f"Face embedding extraction error: {e}")
        # Try with different backend if OpenCV fails
        try:
            embedding_objs = DeepFace.represent(
                img_path=image_array,
                model_name="Facenet",
                detector_backend="retinaface",  # Alternative backend
                enforce_detection=enforce_detection,
                align=False
            )
            if embedding_objs and len(embedding_objs) > 0:
                return np.array(embedding_objs[0]["embedding"])
        except Exception as e2:
            print(f"DeepFace fallback error: {e2}")
        return None


def detect_faces_deepface(image_array):
    """
    Detect faces using DeepFace
    
    Returns:
        List of face regions in format: [x, y, w, h]
    """
    if not DEEPFACE_AVAILABLE:
        return []
        
    try:
        face_objs = DeepFace.extract_faces(
            img_path=image_array,
            detector_backend="opencv",
            enforce_detection=False,
            align=False  # Skip alignment for faster processing
        )
        
        faces = []
        for face_obj in face_objs:
            region = face_obj["facial_area"]
            faces.append([
                region["x"],
                region["y"],
                region["w"],
                region["h"]
            ])
        
        return faces
        
    except Exception as e:
        print(f"Face detection error: {e}")
        return []


def compare_embeddings(embedding1, embedding2, threshold=0.75):
    """
    Compare two face embeddings using cosine similarity
    
    Args:
        embedding1, embedding2: Face embeddings (numpy arrays)
        threshold: Similarity threshold (0-1). Higher = more strict
                  0.8 is very strict, 0.7 is moderate, 0.6 is lenient
    
    Returns:
        (is_match: bool, similarity: float)
    """
    try:
        if embedding1 is None or embedding2 is None:
            return False, 0.0
        
        # Normalize embeddings
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2)
        
        # Ensure similarity is between 0 and 1
        similarity = float(max(0, min(1, similarity)))
        
        is_match = similarity >= threshold
        
        return is_match, similarity
        
    except Exception as e:
        print(f"Embedding comparison error: {e}")
        return False, 0.0


def load_image_from_path_or_url(image_path):
    """Load image from local path or Cloudinary URL"""
    try:
        if image_path.startswith('http://') or image_path.startswith('https://'):
            import requests
            response = requests.get(image_path)
            image = Image.open(io.BytesIO(response.content))
            return np.array(image.convert('RGB'))
        else:
            full_path = os.path.join(settings.MEDIA_ROOT, image_path)
            if os.path.exists(full_path):
                image = cv2.imread(full_path)
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return None
    except Exception as e:
        print(f"Error loading image: {e}")
        return None


# ========================================
# FALLBACK FUNCTIONS (Improved OpenCV)
# ========================================

def add_student_opencv_fallback(request, data):
    """Fallback to improved OpenCV when DeepFace not available"""
    try:
        from . import views  # Import original views for fallback
        
        # Use the improved OpenCV system from views.py
        return views.add_student(request)
    except Exception as e:
        return JsonResponse({"error": f"Fallback error: {str(e)}"}, status=400)


def take_attendance_opencv_fallback(request):
    """Fallback to improved OpenCV when DeepFace not available"""
    try:
        from . import views  # Import original views for fallback
        
        # Use the improved OpenCV system from views.py
        return views.take_attendance_with_session(request)
    except Exception as e:
        return JsonResponse({"error": f"Fallback error: {str(e)}"}, status=400)


# ========================================
# DJANGO VIEW FUNCTIONS
# ========================================

@login_required
@csrf_exempt
def add_student_deepface(request):
    """Add student with DeepFace embedding (fallback to improved OpenCV)"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            student_name = data.get("name")
            student_id = data.get("student_id", "")
            email = data.get("email", "")
            phone = data.get("phone", "")
            
            if not student_name or not image_data:
                return JsonResponse({"error": "Name and image are required"}, status=400)
            
            # Fallback to improved OpenCV if DeepFace not available
            if not DEEPFACE_AVAILABLE:
                return add_student_opencv_fallback(request, data)
            
            # Decode base64 image
            try:
                image_data_clean = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data_clean)
                image = Image.open(io.BytesIO(image_bytes))
                image_array = np.array(image.convert('RGB'))
            except Exception as e:
                return JsonResponse({"error": "Invalid image format"}, status=400)
            
            # Extract face embedding
            embedding = extract_face_embedding_deepface(image_array, enforce_detection=True)
            
            if embedding is None:
                return JsonResponse({
                    "error": "No face detected. Please ensure:\n" +
                            "• Your face is clearly visible\n" +
                            "• Good lighting (no shadows)\n" +
                            "• Look directly at camera\n" +
                            "• Remove sunglasses/masks"
                }, status=400)
            
            # Save image to storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{student_name.lower().replace(' ', '_')}_{timestamp}.jpg"
            
            if image.mode != 'RGB':
                if image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                else:
                    image = image.convert('RGB')
            
            # Try Cloudinary first, fallback to local
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG', quality=95)
                img_byte_arr.seek(0)
                
                upload_result = cloudinary.uploader.upload(
                    img_byte_arr,
                    folder="attendance_students",
                    public_id=filename.replace('.jpg', ''),
                    resource_type="image"
                )
                relative_path = upload_result['secure_url']
            except Exception as cloudinary_error:
                file_path = os.path.join(settings.MEDIA_ROOT, 'students', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                image.save(file_path, 'JPEG', quality=95)
                relative_path = os.path.join('students', filename)
            
            # Store embedding as JSON
            embedding_json = json.dumps(embedding.tolist())
            
            # Create student record
            student = Student.objects.create(
                name=student_name,
                student_id=student_id if student_id else None,
                email=email if email else None,
                phone=phone if phone else None,
                image_path=relative_path,
                face_encoding=embedding_json  # Store DeepFace embedding
            )
            
            # Auto-add to teacher's classes
            teacher_classes = Class.objects.filter(teacher=request.user, is_active=True)
            if teacher_classes.exists():
                student.classes.add(*teacher_classes)
            
            return JsonResponse({
                "message": f"Student {student_name} added successfully with DeepFace recognition!",
                "student_id": student.id
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@login_required
@csrf_exempt
def take_attendance_deepface(request):
    """Take attendance with DeepFace recognition (fallback to improved OpenCV)"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            session_id = data.get("session_id")
            
            if not image_data or not session_id:
                return JsonResponse({"error": "Missing required data"}, status=400)
            
            # Fallback to improved OpenCV if DeepFace not available
            if not DEEPFACE_AVAILABLE:
                return take_attendance_opencv_fallback(request)
            
            # Get session
            try:
                session = AttendanceSession.objects.get(id=session_id, teacher=request.user)
            except AttendanceSession.DoesNotExist:
                return JsonResponse({"error": "Session not found"}, status=400)
            
            # Decode image
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Extract embedding from captured image
            captured_embedding = extract_face_embedding_deepface(rgb_frame, enforce_detection=False)
            
            if captured_embedding is None:
                return JsonResponse({
                    "message": "No face detected in camera. Please:\n" +
                              "• Position face clearly in frame\n" +
                              "• Ensure good lighting\n" +
                              "• Look directly at camera",
                    "faces": []
                })
            
            # Get students in this class with embeddings
            students = session.class_session.students.filter(is_active=True)
            
            best_match = None
            best_similarity = 0.0
            SIMILARITY_THRESHOLD = 0.75  # Adjust: 0.8 = very strict, 0.7 = moderate, 0.6 = lenient
            
            for student in students:
                if not student.face_encoding:
                    continue
                
                try:
                    # Load stored embedding
                    stored_embedding = np.array(json.loads(student.face_encoding))
                    
                    # Compare embeddings
                    is_match, similarity = compare_embeddings(
                        captured_embedding, 
                        stored_embedding,
                        threshold=SIMILARITY_THRESHOLD
                    )
                    
                    if is_match and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = student
                        
                except Exception as e:
                    print(f"Error comparing with {student.name}: {e}")
                    continue
            
            # Detect faces for visualization
            faces = detect_faces_deepface(rgb_frame)
            faces_for_js = [
                {"top": f[1], "right": f[0]+f[2], "bottom": f[1]+f[3], "left": f[0]}
                for f in faces
            ]
            
            if not best_match:
                return JsonResponse({
                    "message": f"No match found - Face not recognized (threshold: {SIMILARITY_THRESHOLD*100:.0f}%)",
                    "faces": faces_for_js
                })
            
            # Process attendance
            current_time = datetime.now()
            
            existing_record = AttendanceRecord.objects.filter(
                student=best_match,
                session=session
            ).first()
            
            if not existing_record:
                arrival_time = current_time.time()
                is_late = arrival_time > session.start_time
                
                AttendanceRecord.objects.create(
                    student=best_match,
                    session=session,
                    arrival_time=arrival_time,
                    is_late=is_late
                )
                
                time_str = arrival_time.strftime("%H:%M:%S")
                status = f" (Late - {time_str})" if is_late else f" (On time - {time_str})"
                confidence_str = f" [Match: {best_similarity*100:.1f}%]"
                message = f"Attendance taken: {best_match.name}{status}{confidence_str}"
            else:
                original_time = existing_record.arrival_time.strftime("%H:%M:%S")
                message = f"{best_match.name} (Already marked at {original_time})"
            
            # Get updated counts
            total_attendance = AttendanceRecord.objects.filter(session=session).count()
            total_students = session.class_session.students.filter(is_active=True).count()
            
            return JsonResponse({
                "message": message,
                "faces": faces_for_js,
                "attendance_count": total_attendance,
                "total_students": total_students,
                "confidence": float(best_similarity)
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ========================================
# RENDER DEPLOYMENT OPTIMIZATION
# ========================================

"""
requirements.txt for Render free tier:

deepface==0.0.79
tf-keras==2.16.0
opencv-python-headless==4.8.1.78
Pillow==10.1.0
numpy==1.24.3

Build command in render.yaml:
build: pip install --upgrade pip && pip install -r requirements.txt

Memory optimization tips:
1. Use opencv backend (not mtcnn or retinaface)
2. Use Facenet model (22MB) instead of VGG-Face (528MB)
3. Set enforce_detection=False for faster processing
4. Consider caching embeddings in memory for active sessions
"""

# Optional: Cache for better performance
from functools import lru_cache

@lru_cache(maxsize=100)
def get_student_embedding_cached(student_id):
    """Cache student embeddings to avoid repeated JSON parsing"""
    try:
        student = Student.objects.get(id=student_id)
        if student.face_encoding:
            return np.array(json.loads(student.face_encoding))
    except:
        pass
    return None
