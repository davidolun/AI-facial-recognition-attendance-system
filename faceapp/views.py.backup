import base64
import re
import time
import logging
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os
import datetime
import json
import cloudinary
import cloudinary.uploader
from cloudinary import config as cloudinary_config

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env")
except ImportError:
    print("⚠️ python-dotenv not available")
except Exception as e:
    print(f"⚠️ Error loading .env: {e}")

# Configure Cloudinary
cloudinary_config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Import image processing libraries
try:
    import numpy as np
    import cv2
    from PIL import Image
    import io
    import boto3
    from botocore.exceptions import ClientError
    IMAGE_PROCESSING_AVAILABLE = True
    FACE_RECOGNITION_AVAILABLE = True
    print("✅ Image processing libraries loaded (AWS Rekognition)")
except ImportError as e:
    IMAGE_PROCESSING_AVAILABLE = False
    FACE_RECOGNITION_AVAILABLE = False
    print(f"Warning: Image processing libraries not available: {e}")

# Initialize AWS Rekognition client
rekognition_client = None
s3_client = None
AWS_CONFIGURED = False

try:
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-west-1')
    AWS_COLLECTION_ID = os.getenv('AWS_FACE_COLLECTION_ID', 'attendance-faces')
    
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        rekognition_client = boto3.client(
            'rekognition',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        
        # Create collection if it doesn't exist
        try:
            rekognition_client.describe_collection(CollectionId=AWS_COLLECTION_ID)
            print(f"✅ AWS Rekognition collection '{AWS_COLLECTION_ID}' exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                rekognition_client.create_collection(CollectionId=AWS_COLLECTION_ID)
                print(f"✅ Created AWS Rekognition collection '{AWS_COLLECTION_ID}'")
            else:
                print(f"Error checking collection: {e}")
        
        AWS_CONFIGURED = True
        print("✅ AWS Rekognition configured successfully")
    else:
        print("⚠️ AWS credentials not found in environment variables")
except Exception as e:
    print(f"⚠️ AWS Rekognition initialization failed: {e}")
    AWS_CONFIGURED = False

# OpenAI availability
OPENAI_AVAILABLE = False
if os.getenv('DISABLE_OPENAI', 'false').lower() != 'true':
    try:
        from openai import OpenAI
        OPENAI_AVAILABLE = True
    except ImportError:
        OPENAI_AVAILABLE = False
        print("Warning: OpenAI not available. AI features will be disabled.")

# Office document libraries
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

from django.db.models import Count, Q
from datetime import datetime, date, timedelta
from .models import Student, AttendanceRecord, AttendanceSession, AIQuery
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from .models import Teacher, Class
from django.db import transaction

# Set up loggers
logger = logging.getLogger('faceapp')
performance_logger = logging.getLogger('faceapp.performance')
security_logger = logging.getLogger('faceapp.security')

client = None

# ========================================
# AWS REKOGNITION FACE RECOGNITION FUNCTIONS
# ========================================

def detect_faces_rekognition(image_bytes):
    """Detect faces using AWS Rekognition"""
    if not AWS_CONFIGURED or not rekognition_client:
        print("❌ AWS Rekognition not configured")
        return []
    
    try:
        response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['DEFAULT']
        )
        
        faces = []
        for face_detail in response['FaceDetails']:
            bbox = face_detail['BoundingBox']
            faces.append({
                'left': bbox['Left'],
                'top': bbox['Top'],
                'width': bbox['Width'],
                'height': bbox['Height'],
                'confidence': face_detail['Confidence']
            })
        
        print(f"✅ Detected {len(faces)} faces with AWS Rekognition")
        return faces
        
    except ClientError as e:
        print(f"❌ AWS Rekognition face detection error: {e}")
        return []
    except Exception as e:
        print(f"❌ Face detection error: {e}")
        return []


def index_face_rekognition(image_bytes, student_id, student_name):
    """Index a face in AWS Rekognition collection"""
    if not AWS_CONFIGURED or not rekognition_client:
        print("❌ AWS Rekognition not configured")
        return None
    
    try:
        response = rekognition_client.index_faces(
            CollectionId=AWS_COLLECTION_ID,
            Image={'Bytes': image_bytes},
            ExternalImageId=str(student_id),
            DetectionAttributes=['DEFAULT'],
            MaxFaces=1,
            QualityFilter='AUTO'
        )
        print(f"📊 AWS Response: {response}") 
        if response['FaceRecords']:
            face_id = response['FaceRecords'][0]['Face']['FaceId']
            print(f"✅ Indexed face for {student_name} (Face ID: {face_id})")
            print(f"✅ ExternalImageId stored: {student_id}") 
            return face_id
        else:
            print(f"❌ No face detected for {student_name}")
            return None
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'InvalidParameterException':
            print(f"❌ Invalid image format or no face detected: {e}")
        else:
            print(f"❌ AWS Rekognition indexing error: {e}")
        return None
    except Exception as e:
        print(f"❌ Face indexing error: {e}")
        return None


def search_face_rekognition(image_bytes, threshold=80):
    """Search for a face in AWS Rekognition collection"""
    if not AWS_CONFIGURED or not rekognition_client:
        print("❌ AWS Rekognition not configured")
        return None, 0
    
    try:
        response = rekognition_client.search_faces_by_image(
            CollectionId=AWS_COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=threshold
        )
        print(f"📊 Search response: {response}")  # ✅ ADD THIS
        print(f"🎯 Matches found: {len(response.get('FaceMatches', []))}")
        if response['FaceMatches']:
            match = response['FaceMatches'][0]
            student_id = match['Face']['ExternalImageId']
            similarity = match['Similarity']
            
            print(f"✅ Face match found: Student ID {student_id}, Similarity: {similarity:.2f}%")
            return student_id, similarity
        else:
            print(f"❌ No face match found (threshold: {threshold}%)")
            return None, 0
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'InvalidParameterException':
            print(f"❌ No face detected in image: {e}")
        else:
            print(f"❌ AWS Rekognition search error: {e}")
        return None, 0
    except Exception as e:
        print(f"❌ Face search error: {e}")
        return None, 0


def delete_face_rekognition(face_id):
    """Delete a face from AWS Rekognition collection"""
    if not AWS_CONFIGURED or not rekognition_client:
        print("❌ AWS Rekognition not configured")
        return False
    
    try:
        rekognition_client.delete_faces(
            CollectionId=AWS_COLLECTION_ID,
            FaceIds=[face_id]
        )
        print(f"✅ Deleted face {face_id} from collection")
        return True
        
    except ClientError as e:
        print(f"❌ Error deleting face: {e}")
        return False


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
# MAIN VIEW FUNCTIONS
# ========================================

@login_required
def home(request):
    start_time = time.time()
    logger.info(f"User {request.user.username} accessed home page")
    response = render(request, 'home.html')
    performance_logger.info(f"Home page load time: {time.time() - start_time:.2f}s for user {request.user.username}")
    return response


@login_required
@csrf_exempt
def add_student(request):
    start_time = time.time()
    logger.info(f"User {request.user.username} initiated student addition")

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            student_name = data.get("name")
            student_id = data.get("student_id", "")
            email = data.get("email", "")
            phone = data.get("phone", "")

            if not student_name:
                logger.warning(f"Student addition failed: No name provided by user {request.user.username}")
                return JsonResponse({"error": "No name provided"}, status=400)
            if not image_data:
                logger.warning(f"Student addition failed: No image provided by user {request.user.username}")
                return JsonResponse({"error": "No image provided"}, status=400)

            if not AWS_CONFIGURED:
                logger.error("AWS Rekognition not configured")
                return JsonResponse({"error": "Face recognition service not configured"}, status=500)

            # Decode base64 image
            try:
                image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                logger.error(f"Image decoding failed for user {request.user.username}: {str(e)}")
                return JsonResponse({"error": "Invalid image format"}, status=400)

            # Convert to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert image to bytes for AWS
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr.seek(0)
            aws_image_bytes = img_byte_arr.read()

            # Generate unique student ID if not provided
            if not student_id:
                student_id = f"STU{int(time.time())}"

            # Index face in AWS Rekognition
            try:
                face_id = index_face_rekognition(aws_image_bytes, student_id, student_name)
                
                if face_id is None:
                    logger.warning(f"No face detected in image for {student_name}")
                    return JsonResponse({
                        "error": "No face detected. Please ensure:\n• Your face is clearly visible\n• Good lighting (no shadows)\n• Look directly at camera\n• Remove sunglasses/masks"
                    }, status=400)
                
                logger.info(f"Face indexed for {student_name} (Face ID: {face_id})")
                    
            except Exception as e:
                logger.error(f"Face detection failed for {student_name}: {str(e)}")
                return JsonResponse({"error": "Face detection failed. Please try again with better lighting."}, status=400)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{student_name.lower().replace(' ', '_')}_{timestamp}.jpg"
            
            # Try to upload to Cloudinary first, fallback to local storage
            try:
                logger.info(f"Attempting to upload {filename} to Cloudinary...")
                img_byte_arr.seek(0)
                
                upload_result = cloudinary.uploader.upload(
                    img_byte_arr,
                    folder="attendance_students",
                    public_id=filename.replace('.jpg', ''),
                    resource_type="image"
                )
                relative_path = upload_result['secure_url']
                logger.info(f"Successfully uploaded to Cloudinary: {relative_path}")
            except Exception as cloudinary_error:
                logger.warning(f"Cloudinary upload failed: {cloudinary_error}. Saving locally...")
                file_path = os.path.join(settings.MEDIA_ROOT, 'students', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                image.save(file_path, 'JPEG', quality=95)
                relative_path = os.path.join('students', filename)
                logger.info(f"Saved locally: {relative_path}")

            # Upload to AWS S3 bucket
            

            # S3 upload optional - Rekognition stores faces in its own collection
            logger.info("Face indexed in Rekognition collection (S3 upload skipped)")
            # Store AWS Face ID as face encoding
            face_encoding_data = json.dumps({
                'face_id': face_id,
                'student_id': student_id,
                'indexed_at': datetime.now().isoformat(),
                'service': 'aws_rekognition'
            })

            # Create student record
            student = Student.objects.create(
                name=student_name,
                student_id=student_id,
                email=email if email else None,
                phone=phone if phone else None,
                image_path=relative_path,
                face_encoding=face_encoding_data
            )

            # Automatically add student to all classes of the logged-in teacher
            teacher_classes = Class.objects.filter(teacher=request.user, is_active=True)
            if teacher_classes.exists():
                student.classes.add(*teacher_classes)
                logger.info(f"Student {student_name} automatically added to {teacher_classes.count()} classes")

            processing_time = time.time() - start_time
            logger.info(f"Student {student_name} added successfully in {processing_time:.2f}s")
            
            return JsonResponse({
                "message": f"Student {student_name} added successfully!",
                "student_id": student.id,
                "processing_time": f"{processing_time:.2f}s"
            })

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Student addition failed after {processing_time:.2f}s: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)
    
    return render(request, "add_student.html")


@login_required
@csrf_exempt
def take_attendance_with_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            session_id = data.get("session_id")
            
            if not image_data:
                return JsonResponse({"error": "No image received"}, status=400)
            
            if not session_id:
                return JsonResponse({"error": "No session selected"}, status=400)

            if not AWS_CONFIGURED:
                return JsonResponse({"error": "Face recognition service not configured"}, status=500)

            try:
                session = AttendanceSession.objects.get(id=session_id, teacher=request.user)
            except AttendanceSession.DoesNotExist:
                return JsonResponse({"error": "Session not found or you do not have permission"}, status=400)

            # Decode image
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)

            # Search for face in AWS Rekognition
            print("Searching for face in AWS Rekognition collection...")
            matched_student_id, similarity = search_face_rekognition(img_bytes, threshold=80)
            
            if not matched_student_id:
                print("Trying with lower threshold (70%)...")
                matched_student_id, similarity = search_face_rekognition(img_bytes, threshold=70)
            
            # Detect faces for visualization
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            pil_image = Image.fromarray(rgb_frame)
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            detect_bytes = img_byte_arr.read()
            
            detected_faces = detect_faces_rekognition(detect_bytes)
            
            # Convert to frontend format
            height, width = rgb_frame.shape[:2]
            faces_for_js = []
            for face in detected_faces:
                faces_for_js.append({
                    "top": int(face['top'] * height),
                    "right": int((face['left'] + face['width']) * width),
                    "bottom": int((face['top'] + face['height']) * height),
                    "left": int(face['left'] * width)
                })
            
            if not matched_student_id:
                print(f"\n❌ NO MATCH FOUND")
                print(f"Best similarity: {similarity:.2f}%")
                return JsonResponse({
                    "message": f"No match found - Face not recognized\nBest similarity: {similarity:.1f}%\nThreshold: 70%",
                    "faces": faces_for_js,
                    "debug": {
                        "best_similarity": float(similarity),
                        "threshold": 70,
                        "service": "aws_rekognition"
                    }
                })

            # Find student by student_id
            try:
                best_match = Student.objects.get(student_id=matched_student_id, is_active=True)
            except Student.DoesNotExist:
                print(f"❌ Student with ID {matched_student_id} not found in database")
                return JsonResponse({
                    "message": "Student record not found in database",
                    "faces": faces_for_js
                })
            
            # Check if student is in this class
            if not session.class_session.students.filter(id=best_match.id).exists():
                return JsonResponse({
                    "message": f"{best_match.name} is not enrolled in {session.class_session.name}",
                    "faces": faces_for_js
                })
            
            print(f"\n✅ MATCH FOUND: {best_match.name} ({similarity:.2f}%)")
            
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
                confidence_str = f" [Confidence: {similarity:.1f}%]"
                message = f"Attendance taken: {best_match.name}{status}{confidence_str}"
            else:
                original_time = existing_record.arrival_time.strftime("%H:%M:%S")
                message = f"{best_match.name} (Already marked at {original_time})"
            
            total_attendance = AttendanceRecord.objects.filter(session=session).count()
            total_students = session.class_session.students.filter(is_active=True).count()

            return JsonResponse({
                "message": message,
                "faces": faces_for_js,
                "attendance_count": total_attendance,
                "total_students": total_students,
                "session_name": session.name,
                "class_name": session.class_session.name,
                "confidence": float(similarity)
            })

        except Exception as e:
            print(f"❌ ATTENDANCE ERROR: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"message": "Use POST request."})


@csrf_exempt
def detect_faces(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            if not image_data:
                return JsonResponse({"faces": []})

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)

            detected_faces = detect_faces_rekognition(img_bytes)
            
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            height, width = frame.shape[:2]
            
            faces_list = []
            for face in detected_faces:
                faces_list.append({
                    "top": int(face['top'] * height),
                    "right": int((face['left'] + face['width']) * width),
                    "bottom": int((face['top'] + face['height']) * height),
                    "left": int(face['left'] * width)
                })

            return JsonResponse({"faces": faces_list})
        except Exception as e:
            return JsonResponse({"error": str(e), "faces": []})
    return JsonResponse({"faces": []})


# ========================================
# REST OF THE VIEWS (unchanged)
# ========================================
# Include all remaining view functions from the original code
# (class_management, get_teacher_classes, create_session, etc.)

# ========================================
# REST OF THE VIEWS (Class Management, Sessions, etc.)
# ========================================

@login_required
def class_management(request):
    """Render the class management page"""
    return render(request, 'class_management.html')


@login_required
@csrf_exempt
def create_class(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            code = data.get('code', '').strip()
            description = data.get('description', '').strip()
            academic_year = data.get('academic_year', '2024-2025').strip()
            semester = data.get('semester', 'Fall').strip()
            
            if not name or not code:
                return JsonResponse({'error': 'Class name and code are required'}, status=400)
            
            if Class.objects.filter(teacher=request.user, code=code).exists():
                return JsonResponse({'error': 'You already have a class with this code'}, status=400)
            
            new_class = Class.objects.create(
                name=name,
                code=code,
                teacher=request.user,
                description=description,
                academic_year=academic_year,
                semester=semester
            )

            existing_students = Student.objects.filter(classes__teacher=request.user).distinct()
            if existing_students.exists():
                new_class.students.add(*existing_students)
            
            return JsonResponse({
                'message': f'Class "{name}" created successfully!',
                'class_id': new_class.id,
                'class_data': {
                    'id': new_class.id,
                    'name': new_class.name,
                    'code': new_class.code,
                    'student_count': new_class.students.count()
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def get_teacher_classes(request):
    """Get classes for the logged-in teacher"""
    try:
        classes = Class.objects.filter(teacher=request.user, is_active=True)
        classes_data = []
        
        for cls in classes:
            student_count = cls.students.filter(is_active=True).count()
            session_count = cls.sessions.count()
            
            classes_data.append({
                'id': cls.id,
                'name': cls.name,
                'code': cls.code,
                'description': cls.description,
                'academic_year': cls.academic_year,
                'semester': cls.semester,
                'student_count': student_count,
                'session_count': session_count,
                'created_at': cls.created_at.strftime('%Y-%m-%d')
            })
        
        return JsonResponse({
            'classes': classes_data,
            'teacher': {
                'name': request.user.get_full_name(),
                'username': request.user.username,
                'department': request.user.department
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def assign_student_to_class(request):
    """Assign a student to one of teacher's classes"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            class_id = data.get('class_id')
            
            if not student_id or not class_id:
                return JsonResponse({'error': 'Student ID and Class ID are required'}, status=400)
            
            try:
                class_obj = Class.objects.get(id=class_id, teacher=request.user)
            except Class.DoesNotExist:
                return JsonResponse({'error': 'Class not found or you do not have permission'}, status=404)
            
            try:
                student = Student.objects.get(id=student_id, is_active=True)
            except Student.DoesNotExist:
                return JsonResponse({'error': 'Student not found'}, status=404)
            
            class_obj.students.add(student)
            
            return JsonResponse({
                'message': f'{student.name} assigned to {class_obj.name} successfully!',
                'class_name': class_obj.name,
                'student_name': student.name
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@csrf_exempt
def remove_student_from_class(request):
    """Remove a student from teacher's classes"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            class_id = data.get('class_id')
            
            if not student_id:
                return JsonResponse({'error': 'Student ID is required'}, status=400)
            
            try:
                student = Student.objects.get(id=student_id, is_active=True)
            except Student.DoesNotExist:
                return JsonResponse({'error': 'Student not found'}, status=404)
            
            if class_id:
                try:
                    class_obj = Class.objects.get(id=class_id, teacher=request.user)
                    class_obj.students.remove(student)
                    return JsonResponse({
                        'message': f'{student.name} removed from {class_obj.name} successfully!'
                    })
                except Class.DoesNotExist:
                    return JsonResponse({'error': 'Class not found'}, status=404)
            else:
                teacher_classes = Class.objects.filter(teacher=request.user, students=student)
                removed_classes = []
                
                for class_obj in teacher_classes:
                    class_obj.students.remove(student)
                    removed_classes.append(class_obj.name)
                
                if removed_classes:
                    return JsonResponse({
                        'message': f'{student.name} removed from classes: {", ".join(removed_classes)}'
                    })
                else:
                    return JsonResponse({
                        'message': f'{student.name} was not in any of your classes'
                    })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def get_all_students(request):
    """Get all students in the system"""
    try:
        all_students = Student.objects.filter(is_active=True).prefetch_related('classes')
        students_data = []
        
        for student in all_students:
            current_classes = student.classes.filter(is_active=True)
            teacher_classes = current_classes.filter(teacher=request.user)
            is_in_teacher_classes = teacher_classes.exists()
            
            students_data.append({
                'id': student.id,
                'name': student.name,
                'student_id': student.student_id,
                'email': student.email,
                'phone': student.phone,
                'created_at': student.created_at.strftime('%Y-%m-%d'),
                'current_classes': [
                    {
                        'id': cls.id,
                        'name': cls.name,
                        'code': cls.code,
                        'teacher_name': cls.teacher.get_full_name()
                    }
                    for cls in current_classes
                ],
                'is_in_teacher_classes': is_in_teacher_classes,
                'teacher_classes': [
                    {
                        'id': cls.id,
                        'name': cls.name,
                        'code': cls.code
                    }
                    for cls in teacher_classes
                ]
            })
        
        return JsonResponse({
            'students': students_data,
            'total_students': len(students_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def get_teacher_students(request):
    """Get all students in the logged-in teacher's classes"""
    try:
        students = Student.objects.filter(
            classes__teacher=request.user,
            is_active=True
        ).distinct().prefetch_related('classes')
        
        students_data = []
        
        for student in students:
            student_classes = student.classes.filter(teacher=request.user, is_active=True)
            
            students_data.append({
                'id': student.id,
                'name': student.name,
                'student_id': student.student_id,
                'email': student.email,
                'phone': student.phone,
                'created_at': student.created_at.strftime('%Y-%m-%d'),
                'classes': [
                    {
                        'id': cls.id,
                        'name': cls.name,
                        'code': cls.code
                    }
                    for cls in student_classes
                ]
            })
        
        return JsonResponse({
            'students': students_data,
            'total_students': len(students_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ========================================
# SESSION MANAGEMENT
# ========================================

@login_required
@csrf_exempt
def create_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            date_str = data.get("date")
            start_time_str = data.get("start_time")
            end_time_str = data.get("end_time", "")
            class_id = data.get("class_id")
            session_type = data.get("session_type", "Regular")
            
            if not name or not date_str or not start_time_str or not class_id:
                return JsonResponse({"error": "Missing required fields"}, status=400)
            
            try:
                class_obj = Class.objects.get(id=class_id, teacher=request.user)
            except Class.DoesNotExist:
                return JsonResponse({"error": "Class not found or you do not have permission"}, status=404)
            
            session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time() if end_time_str else None
            
            enhanced_name = f"{name} ({session_type})" if session_type != "Regular" else name
            
            session = AttendanceSession.objects.create(
                name=enhanced_name,
                date=session_date,
                start_time=start_time,
                end_time=end_time,
                teacher=request.user,
                class_session=class_obj
            )
            
            return JsonResponse({
                "message": f"Session '{enhanced_name}' created successfully for {class_obj.name}",
                "session_id": session.id,
                "session_data": {
                    "id": session.id,
                    "name": enhanced_name,
                    "class_name": class_obj.name,
                    "date": session_date.strftime('%Y-%m-%d'),
                    "start_time": start_time.strftime('%H:%M'),
                    "end_time": end_time.strftime('%H:%M') if end_time else None,
                }
            })
            
        except ValueError as e:
            return JsonResponse({"error": "Invalid date/time format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Use POST request"}, status=405)


@login_required
@csrf_exempt
def get_sessions(request):
    """Get sessions for the logged-in teacher only"""
    if request.method == "GET":
        try:
            today = date.today()
            upcoming_date = today + timedelta(days=7)
            
            sessions = AttendanceSession.objects.filter(
                teacher=request.user,
                date__gte=today,
                date__lte=upcoming_date
            ).order_by('date', 'start_time')
            
            session_data = []
            for session in sessions:
                attendance_records = AttendanceRecord.objects.filter(session=session)
                unique_attendees = attendance_records.values_list('student_id', flat=True).distinct().count()
                total_students = session.class_session.students.filter(is_active=True).count()
                
                session_data.append({
                    'id': session.id,
                    'name': session.name,
                    'class_name': session.class_session.name,
                    'date': session.date.strftime('%Y-%m-%d'),
                    'date_display': session.date.strftime('%B %d, %Y'),
                    'start_time': session.start_time.strftime('%H:%M'),
                    'end_time': session.end_time.strftime('%H:%M') if session.end_time else 'Ongoing',
                    'attendance_count': unique_attendees,
                    'total_students': total_students,
                    'is_today': session.date == today,
                    'is_past': session.date < today,
                    'status': 'Active' if session.date == today else 'Upcoming'
                })
            
            return JsonResponse({
                'sessions': session_data,
                'today': today.strftime('%Y-%m-%d')
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ========================================
# AUTHENTICATION
# ========================================

@csrf_exempt
def signup_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
            confirm_password = data.get('confirm_password', '').strip()
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            phone = data.get('phone', '').strip()
            department = data.get('department', '').strip()
            employee_id = data.get('employee_id', '').strip()
            
            validation_errors = []
            
            if not username:
                validation_errors.append('Username is required')
            elif len(username) < 3:
                validation_errors.append('Username must be at least 3 characters long')
            
            if not email or '@' not in email:
                validation_errors.append('Valid email address is required')
            
            if not first_name or len(first_name.strip()) < 2:
                validation_errors.append('First name must be at least 2 characters long')
            
            if not last_name or len(last_name.strip()) < 2:
                validation_errors.append('Last name must be at least 2 characters long')
            
            if not department or len(department.strip()) < 2:
                validation_errors.append('Department is required')
            
            if not password:
                validation_errors.append('Password is required')
            elif len(password) < 8:
                validation_errors.append('Password must be at least 8 characters long')
            
            if password != confirm_password:
                validation_errors.append('Passwords do not match')
            
            if username and Teacher.objects.filter(username=username).exists():
                validation_errors.append('Username already exists')
            
            if email and Teacher.objects.filter(email=email).exists():
                validation_errors.append('Email address is already registered')
            
            if employee_id and Teacher.objects.filter(employee_id=employee_id).exists():
                validation_errors.append('Employee ID already exists')
            
            if validation_errors:
                return JsonResponse({'error': validation_errors[0]}, status=400)
            
            with transaction.atomic():
                teacher = Teacher.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    department=department,
                    employee_id=employee_id if employee_id else None
                )
                
                login(request, teacher)
                
            return JsonResponse({
                'message': 'Account created successfully!',
                'redirect': '/dashboard/'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return render(request, 'auth/signup.html')


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            if not username or not password:
                security_logger.warning(f"Login attempt failed: Missing credentials")
                return JsonResponse({'error': 'Please enter both username and password'}, status=400)

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                logger.info(f"User {username} logged in successfully")
                return JsonResponse({
                    'message': 'Login successful!',
                    'redirect': '/dashboard/',
                    'user': {
                        'name': user.get_full_name(),
                        'username': user.username,
                        'is_admin': user.is_admin
                    }
                })
            else:
                security_logger.warning(f"Login attempt failed: Invalid credentials for '{username}'")
                return JsonResponse({'error': 'Invalid username or password'}, status=400)

        except Exception as e:
            security_logger.error(f"Login error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    
    return render(request, 'auth/login.html')


@login_required
def logout_view(request):
    logger.info(f"User {request.user.username} logged out")
    logout(request)
    return redirect('/login/')


# ========================================
# DASHBOARD & ANALYTICS
# ========================================

def get_complete_attendance_data(teacher=None):
    """Get COMPLETE attendance data for AI"""
    
    if teacher:
        all_students = list(Student.objects.filter(is_active=True, classes__teacher=teacher).distinct().values('id', 'name', 'student_id', 'email'))
        all_sessions = list(AttendanceSession.objects.filter(teacher=teacher).order_by('-date', '-start_time').values(
            'id', 'name', 'date', 'start_time', 'end_time', 'class_session__name'
        ))
    else:
        all_students = list(Student.objects.filter(is_active=True).values('id', 'name', 'student_id', 'email'))
        all_sessions = list(AttendanceSession.objects.all().order_by('-date', '-start_time').values(
            'id', 'name', 'date', 'start_time', 'end_time', 'class_session__name'
        ))
    
    for session in all_sessions:
        session['date'] = session['date'].strftime('%Y-%m-%d')
        session['start_time'] = session['start_time'].strftime('%H:%M:%S')
        if session['end_time']:
            session['end_time'] = session['end_time'].strftime('%H:%M:%S')
    
    if teacher:
        all_records = list(AttendanceRecord.objects.filter(session__teacher=teacher).select_related('student', 'session').values(
            'student__name', 'student_id', 'session__name', 'session_id', 
            'date', 'time', 'arrival_time', 'is_late', 'timestamp'
        ))
    else:
        all_records = list(AttendanceRecord.objects.select_related('student', 'session').values(
            'student__name', 'student_id', 'session__name', 'session_id', 
            'date', 'time', 'arrival_time', 'is_late', 'timestamp'
        ))
    
    for record in all_records:
        record['date'] = record['date'].strftime('%Y-%m-%d')
        record['time'] = record['time'].strftime('%H:%M:%S')
        record['timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if record['arrival_time']:
            record['arrival_time'] = record['arrival_time'].strftime('%H:%M:%S')
    
    student_stats = {}
    for student in all_students:
        student_records = [r for r in all_records if r['student_id'] == student['id']]
        sessions_attended = len(set(r['session_id'] for r in student_records))
        times_late = len([r for r in student_records if r['is_late']])
        times_on_time = len([r for r in student_records if not r['is_late']])
        
        student_session_ids = set(r['session_id'] for r in student_records)
        
        if teacher:
            current_available_sessions = AttendanceSession.objects.filter(
                teacher=teacher,
                class_session__students__id=student['id']
            ).values_list('id', flat=True)
        else:
            current_available_sessions = AttendanceSession.objects.filter(
                class_session__students__id=student['id']
            ).values_list('id', flat=True)
        
        available_session_count = max(len(student_session_ids), len(list(current_available_sessions)))
        
        if available_session_count > 0:
            attendance_percentage = min(round((sessions_attended / available_session_count) * 100, 1), 100.0)
        else:
            attendance_percentage = 0
        
        student_stats[student['name']] = {
            'total_sessions_attended': sessions_attended,
            'available_sessions': available_session_count,
            'times_late': times_late,
            'times_on_time': times_on_time,
            'attendance_percentage': attendance_percentage
        }
    
    session_details = {}
    for session in all_sessions:
        session_key = f"{session['name']}_{session['date']}"
        session_records = [r for r in all_records if r['session_id'] == session['id']]
        present_students = [r['student__name'] for r in session_records]
        
        if teacher:
            eligible_students = list(Student.objects.filter(
                classes__sessions__id=session['id'], 
                is_active=True
            ).values_list('name', flat=True))
        else:
            eligible_students = [s['name'] for s in all_students]
        
        if not eligible_students:
            eligible_students = present_students
        
        absent_students = [name for name in eligible_students if name not in present_students]
        
        session_details[session_key] = {
            'session_info': session,
            'present_students': present_students,
            'absent_students': absent_students,
            'present_count': len(present_students),
            'absent_count': len(absent_students),
            'eligible_count': len(eligible_students),
            'late_students': [r['student__name'] for r in session_records if r['is_late']],
            'on_time_students': [r['student__name'] for r in session_records if not r['is_late']]
        }
    
    sessions_list = list(set(session['name'] for session in all_sessions))
    unique_dates = sorted(list(set(session['date'] for session in all_sessions)))
    
    return {
        'total_students': len(all_students),
        'total_sessions': len(all_sessions),
        'today_date': date.today().strftime('%Y-%m-%d'),
        'all_students': all_students,
        'all_sessions': all_sessions,
        'all_attendance_records': all_records,
        'student_statistics': student_stats,
        'session_details': session_details,
        'sessions_list': sessions_list,
        'unique_dates': unique_dates
    }


conversation_contexts = {}

def query_attendance_data_with_context(user_query: str, session_id: str, teacher=None) -> str:
    """Enhanced AI query with conversation context"""
    
    data = get_complete_attendance_data(teacher)
    
    if session_id not in conversation_contexts:
        conversation_contexts[session_id] = []
    
    conversation_history = conversation_contexts[session_id]
    conversation_history.append({"role": "user", "content": user_query})
    
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    teacher_info = ""
    if teacher:
        teacher_info = f"""
TEACHER CONTEXT:
You are responding to {teacher.get_full_name()} ({teacher.username}).
Department: {teacher.department or 'Not specified'}
"""

    data_summary = f"""
ATTENDANCE SYSTEM SUMMARY:
- Total Students: {data['total_students']}
- Total Sessions: {data['total_sessions']}
- Current Date: {data['today_date']}
"""

    system_prompt = f"""
You are a helpful AI assistant for a student attendance tracking system.

{teacher_info}
{data_summary}

Answer questions about attendance, absences, late arrivals, and student records professionally.
"""

    try:
        global client
        if OPENAI_AVAILABLE and client is None:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

        if not OPENAI_AVAILABLE or client is None:
            return "AI assistant is currently unavailable. Please try again later."

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-6:])
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_response})
        conversation_contexts[session_id] = conversation_history
        
        AIQuery.objects.create(query=user_query, response=ai_response)
        
        return ai_response
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"


@login_required
@csrf_exempt
def ai_assistant(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_query = data.get("query", "").strip()
            session_id = data.get("session_id", "default")

            if not user_query:
                return JsonResponse({"error": "No query provided"}, status=400)

            teacher = None if request.user.is_admin else request.user
            ai_response = query_attendance_data_with_context(user_query, session_id, teacher)

            return JsonResponse({
                "query": user_query,
                "response": ai_response,
                "session_id": session_id
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, 'ai_assistant.html')


@login_required
def dashboard(request):
    """Render the main dashboard page"""
    needs_onboarding = not request.user.onboarding_completed
    return render(request, 'dashboard.html', {'needs_onboarding': needs_onboarding})


@login_required
@require_http_methods(["GET"])
def dashboard_data(request):
    """API endpoint for dashboard data"""
    try:
        teacher = None if request.user.is_admin else request.user
        data = get_complete_attendance_data(teacher)
        
        data['analytics'] = {
            'total_records': len(data['all_attendance_records']),
            'late_percentage': 0
        }
        
        if data['all_attendance_records']:
            late_records = [r for r in data['all_attendance_records'] if r['is_late']]
            data['analytics']['late_percentage'] = round((len(late_records) / len(data['all_attendance_records'])) * 100, 2)
        
        data['teacher_info'] = {
            'name': request.user.get_full_name(),
            'username': request.user.username,
            'department': request.user.department,
            'is_admin': request.user.is_admin
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def mark_onboarding_complete(request):
    """Mark onboarding as completed"""
    if request.method == 'POST':
        try:
            request.user.onboarding_completed = True
            request.user.save()
            return JsonResponse({'success': True, 'message': 'Onboarding marked as complete'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def view_records(request):
    return render(request, 'ai_assistant.html')


@login_required
def advanced_analytics(request):
    """Render the advanced analytics page"""
    return render(request, 'advanced_analytics.html')


@login_required
def advanced_analytics_data(request):
    """API endpoint for advanced analytics"""
    try:
        teacher = None if request.user.is_admin else request.user
        base_data = get_complete_attendance_data(teacher)
        
        enhanced_data = {
            **base_data,
            'analytics_ready': True
        }
        
        return JsonResponse(enhanced_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def export_data(request):
    """Export attendance data in various formats"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            export_type = data.get("type", "csv")
            date_from = data.get("date_from")
            date_to = data.get("date_to")
            report_title = data.get("title", "Attendance Report")

            teacher = None if request.user.is_admin else request.user
            return generate_export_file(export_type, date_from, date_to, report_title, teacher)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def generate_export_file(export_type, date_from=None, date_to=None, report_title="Attendance Report", teacher=None):
    """Helper function to generate export files"""
    attendance_data = get_complete_attendance_data(teacher)

    if date_from and date_to:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        attendance_data['all_attendance_records'] = [
            record for record in attendance_data['all_attendance_records']
            if date_from_obj <= datetime.strptime(record['date'], '%Y-%m-%d').date() <= date_to_obj
        ]

    if export_type == "csv":
        import csv
        from io import StringIO
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student Name', 'Session', 'Date', 'Time', 'Status', 'Late'])
        for record in attendance_data['all_attendance_records']:
            writer.writerow([
                record['student__name'],
                record['session__name'] if record['session__name'] else 'N/A',
                record['date'],
                record['time'],
                'Present',
                'Yes' if record['is_late'] else 'No'
            ])
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_title}.csv"'
        return response

    return JsonResponse({'error': 'Export type not supported'}, status=400)


def test_onboarding(request):
    """Test page for onboarding system"""
    return render(request, 'test_onboarding.html')