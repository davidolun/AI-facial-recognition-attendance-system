import os
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from PIL import Image
import io
import requests
import numpy as np
import cv2

# AWS Rekognition Configuration
rekognition_client = None
s3_client = None
AWS_CONFIGURED = False

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env")
except ImportError:
    print("⚠️ python-dotenv not available")
except Exception as e:
    print(f"⚠️ Error loading .env: {e}")

# Initialize AWS Rekognition
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
        print(f"📊 Search response: {response}")
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
