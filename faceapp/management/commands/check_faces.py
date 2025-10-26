# your_app/management/commands/check_faces.py
from django.core.management.base import BaseCommand
import boto3
import os
from dotenv import load_dotenv

class Command(BaseCommand):
    help = 'Check faces in AWS Rekognition collection'

    def handle(self, *args, **kwargs):
        load_dotenv()
        
        rekognition_client = boto3.client(
            'rekognition',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-west-1')
        )
        
        collection_id = os.getenv('AWS_FACE_COLLECTION_ID', 'attendance-faces')
        
        try:
            # Get collection info
            collection_info = rekognition_client.describe_collection(
                CollectionId=collection_id
            )
            
            print("\n" + "="*60)
            print(f"📊 COLLECTION: {collection_id}")
            print("="*60)
            print(f"Face Count: {collection_info['FaceCount']}")
            print(f"Created: {collection_info['CreationTimestamp']}")
            print(f"ARN: {collection_info['CollectionARN']}")
            print("="*60 + "\n")
            
            # List all faces
            response = rekognition_client.list_faces(
                CollectionId=collection_id,
                MaxResults=100
            )
            
            faces = response.get('Faces', [])
            
            if faces:
                print(f"✅ Found {len(faces)} faces in collection:\n")
                
                for i, face in enumerate(faces, 1):
                    print(f"{i}. 🆔 Face ID: {face['FaceId']}")
                    print(f"   👤 Student ID (External): {face.get('ExternalImageId', 'N/A')}")
                    print(f"   📅 Indexed At: {face.get('IndexedAt', 'N/A')}")
                    print(f"   🎯 Confidence: {face.get('Confidence', 'N/A')}%")
                    print(f"   📷 Image ID: {face.get('ImageId', 'N/A')}\n")
            else:
                print("⚠️  No faces found in collection")
                
        except Exception as e:
            print(f"❌ Error: {e}")