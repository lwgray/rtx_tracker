"""
Utility to ensure all generated charts are stored on S3 and not in the git repository.
"""

import os
import sys
import boto3
from utils.logger import get_logger
from utils.s3_storage import s3_storage

# Get logger
logger = get_logger(__name__)

def check_s3_configuration():
    """
    Check if S3 is properly configured and accessible
    
    Returns:
        bool: True if S3 is properly configured, False otherwise
    """
    required_env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'S3_BUCKET_NAME']
    
    # Check if required environment variables are set
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("S3 storage cannot be enabled without these variables")
        return False
    
    # Check if S3 is enabled
    if not s3_storage.is_enabled():
        logger.error("S3 storage is not enabled")
        return False
    
    # Test S3 connection
    try:
        # Try to list objects in the bucket
        s3_storage.s3_client.list_objects(Bucket=s3_storage.s3_bucket, MaxKeys=1)
        logger.info(f"Successfully connected to S3 bucket: {s3_storage.s3_bucket}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to S3 bucket: {e}")
        return False

def enforce_s3_storage():
    """
    Update .gitignore to ensure all generated files are excluded from git tracking
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        gitignore_path = os.path.join(project_root, '.gitignore')
        
        # Read the current .gitignore content
        with open(gitignore_path, 'r') as f:
            content = f.read()
        
        # Entries we want to ensure are in .gitignore
        required_entries = [
            "# System files",
            "**/.DS_Store",
            ".env",
            "**/__pycache__/",
            "*.pyc",
            ".idea/",
            ".vscode/",
            "",
            "# Generated files",
            "*.log",
            "logs/debug/",
            "logs/*.log",
            "static/img/*.png",
            "static/img/*.html",
            "models/*.joblib",
            "",
            "# Runtime files",
            "monitoring_state.json",
            "*.db",
        ]
        
        # Check if content already has all required entries
        if all(line.strip() in content for line in required_entries):
            logger.info(".gitignore already contains all required entries")
            return True
        
        # Update .gitignore
        with open(gitignore_path, 'w') as f:
            f.write('\n'.join(required_entries))
        
        logger.info("Updated .gitignore to exclude generated files")
        return True
    except Exception as e:
        logger.error(f"Failed to update .gitignore: {e}")
        return False

if __name__ == "__main__":
    print("Checking S3 configuration...")
    s3_configured = check_s3_configuration()
    
    if s3_configured:
        print("S3 storage is properly configured and accessible")
    else:
        print("ERROR: S3 storage is not properly configured")
        print("Please set the following environment variables:")
        print("  - AWS_ACCESS_KEY_ID")
        print("  - AWS_SECRET_ACCESS_KEY")
        print("  - S3_BUCKET_NAME")
        print("  - AWS_REGION (optional, defaults to us-east-1)")
        sys.exit(1)
    
    print("\nUpdating .gitignore to exclude generated files...")
    gitignore_updated = enforce_s3_storage()
    
    if gitignore_updated:
        print(".gitignore updated successfully")
    else:
        print("WARNING: Failed to update .gitignore")
        sys.exit(1)
    
    print("\nConfiguration complete. Make sure to commit the updated .gitignore:")
    print("git add .gitignore")
    print("git commit -m \"Update .gitignore to exclude generated files\"")
    print("git push origin main")