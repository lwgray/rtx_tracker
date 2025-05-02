"""
S3 integration for RTX 5090 Stock Tracker
"""

import os
import boto3
from botocore.exceptions import ClientError
import io
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

class S3Storage:
    """Class for handling S3 storage operations"""
    
    def __init__(self):
        """Initialize S3 client"""
        self.s3_bucket = os.environ.get('S3_BUCKET_NAME')
        self.s3_region = os.environ.get('AWS_REGION', 'us-east-1')
        self.s3_enabled = self.s3_bucket is not None and len(self.s3_bucket) > 0
        
        # Set up client if enabled
        if self.s3_enabled:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                region_name=self.s3_region
            )
            logger.info(f"S3 storage initialized with bucket: {self.s3_bucket}")
        else:
            logger.info("S3 storage disabled, using local file storage")
            self.s3_client = None
    
    def is_enabled(self):
        """Check if S3 storage is enabled"""
        return self.s3_enabled
    
    def upload_file(self, file_path, object_name=None, content_type=None):
        """
        Upload a file to S3 bucket
        
        Args:
            file_path: Path to the local file
            object_name: S3 object name (if None, file_path basename is used)
            content_type: Content type of the file (for proper serving)
            
        Returns:
            str: Public URL of the file or None if upload failed
        """
        if not self.s3_enabled:
            logger.debug("S3 storage disabled, returning local file path")
            # Return a relative path that would work in templates
            rel_path = os.path.basename(file_path)
            if '/static/' in file_path:
                # Extract the path relative to the static directory
                static_index = file_path.find('/static/')
                if static_index >= 0:
                    rel_path = file_path[static_index+1:]  # Include 'static/'
            return rel_path
        
        # If object_name not provided, use file_path's basename
        if object_name is None:
            object_name = os.path.basename(file_path)
        
        # Determine content type if not provided
        if content_type is None:
            if file_path.endswith('.png'):
                content_type = 'image/png'
            elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif file_path.endswith('.html'):
                content_type = 'text/html'
            else:
                content_type = 'application/octet-stream'
        
        # Upload file
        try:
            extra_args = {
                'ContentType': content_type,
                'ACL': 'public-read'  # Make the file publicly accessible
            }
            
            self.s3_client.upload_file(
                file_path, 
                self.s3_bucket, 
                object_name,
                ExtraArgs=extra_args
            )
            
            # Generate the URL for the uploaded file
            url = f"https://{self.s3_bucket}.s3.amazonaws.com/{object_name}"
            logger.info(f"File uploaded to S3: {url}")
            
            # Clean up local file after successful upload
            try:
                os.remove(file_path)
                logger.debug(f"Removed local file after S3 upload: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove local file after S3 upload: {e}")
            
            return url
        
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return None
    
    def upload_plotly_figure(self, fig, filename, format='png'):
        """
        Upload a Plotly figure directly to S3 without saving locally first
        
        Args:
            fig: Plotly figure object
            filename: Desired filename in S3
            format: File format ('png' or 'html')
            
        Returns:
            str: Public URL of the file or None if upload failed
        """
        if not self.s3_enabled:
            # Save locally since S3 is disabled
            static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img')
            os.makedirs(static_dir, exist_ok=True)
            local_path = os.path.join(static_dir, filename)
            
            try:
                if format == 'png':
                    fig.write_image(local_path)
                elif format == 'html':
                    fig.write_html(local_path)
                else:
                    logger.error(f"Unsupported format: {format}")
                    return None
                
                logger.debug(f"Saved file locally: {local_path}")
                # Return relative path for templates
                return f"static/img/{filename}"
                
            except Exception as e:
                logger.error(f"Error saving file locally: {e}")
                return None
        
        # For S3 upload, we'll create the file in memory
        try:
            # Prepare content type
            content_type = 'image/png' if format == 'png' else 'text/html'
            
            # Create file in memory
            if format == 'png':
                img_bytes = fig.to_image(format='png')
                file_obj = io.BytesIO(img_bytes)
            elif format == 'html':
                html_str = fig.to_html(include_plotlyjs='cdn')
                file_obj = io.BytesIO(html_str.encode('utf-8'))
            else:
                logger.error(f"Unsupported format: {format}")
                return None
            
            # Upload to S3 directly from memory
            self.s3_client.upload_fileobj(
                file_obj,
                self.s3_bucket,
                filename,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read'
                }
            )
            
            # Generate the URL for the uploaded file
            url = f"https://{self.s3_bucket}.s3.amazonaws.com/{filename}"
            logger.info(f"File uploaded to S3: {url}")
            
            return url
            
        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}")
            return None
    
    def delete_file(self, object_name):
        """
        Delete a file from S3 bucket
        
        Args:
            object_name: S3 object name to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not self.s3_enabled:
            logger.warning("S3 storage disabled, cannot delete file from S3")
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=object_name
            )
            logger.info(f"File deleted from S3: {object_name}")
            return True
        
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def cleanup_old_files(self, prefix=None, days=7):
        """
        Delete files older than specified days from S3 bucket
        
        Args:
            prefix: Optional prefix to filter objects (e.g., 'charts/')
            days: Delete files older than this many days
            
        Returns:
            int: Number of files deleted
        """
        if not self.s3_enabled:
            logger.warning("S3 storage disabled, cannot cleanup S3 files")
            return 0
        
        import datetime
        from datetime import timezone
        
        deleted_count = 0
        cutoff_date = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=days)
        
        try:
            # List objects in the bucket with the given prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            params = {'Bucket': self.s3_bucket}
            if prefix:
                params['Prefix'] = prefix
            
            for page in paginator.paginate(**params):
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    # Check if the object is older than the cutoff date
                    if obj['LastModified'] < cutoff_date:
                        self.s3_client.delete_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                        deleted_count += 1
                        logger.debug(f"Deleted old file from S3: {obj['Key']}")
            
            logger.info(f"Cleaned up {deleted_count} old files from S3")
            return deleted_count
        
        except ClientError as e:
            logger.error(f"Error cleaning up old files from S3: {e}")
            return 0

# Create a singleton instance
s3_storage = S3Storage()