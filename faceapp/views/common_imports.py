import base64
import re
import time
import logging
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from datetime import datetime, date, timedelta
import os
import json
import io

import cloudinary
import cloudinary.uploader
from cloudinary import config as cloudinary_config

try:
    import numpy as np
    import cv2
    from PIL import Image
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False

# Configure Cloudinary
cloudinary_config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'duu7pc7s3'),
    api_key=os.getenv('CLOUDINARY_API_KEY', '625655631397579'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET', 'HEE8Or7rvr7SBOv61t5CWsSRUIs')
)

# Models
from ..models import Student, AttendanceRecord, AttendanceSession, AIQuery, Teacher, Class

# Set up loggers
logger = logging.getLogger('faceapp')
performance_logger = logging.getLogger('faceapp.performance')
security_logger = logging.getLogger('faceapp.security')

# Face recognition utilities
from .face_recognition_utils import (
    AWS_CONFIGURED,
    detect_faces_rekognition,
    index_face_rekognition,
    search_face_rekognition,
    delete_face_rekognition
)
