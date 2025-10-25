from django.apps import AppConfig
import os


class FaceappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'faceapp'
    
    def ready(self):
        """Configure TensorFlow and environment for memory efficiency"""
        # Set TensorFlow environment variables to reduce memory usage
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow warnings
        os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
        os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'
        
        # Memory optimization settings
        os.environ['TF_NUM_INTEROP_THREADS'] = '2'
        os.environ['TF_NUM_INTRAOP_THREADS'] = '2'
        
        # Suppress TensorFlow deprecation warnings
        try:
            import tensorflow as tf
            tf.get_logger().setLevel('ERROR')
        except ImportError:
            pass
