"""
Verification script for S3 readiness.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_s3_client_initialization():
    print("Testing S3 client initialization...")
    with patch("boto3.client") as mock_boto:
        # Mock environment
        os.environ["S3_DATA_BUCKET"] = "test-bucket"
        os.environ["AWS_REGION"] = "ap-south-1"
        
        from driftwatch.utils.s3_client import S3Client
        client = S3Client()
        
        assert client.enabled == True
        assert client.bucket == "test-bucket"
        print("  - S3 client initialized and enabled.")

def test_s3_upload_logic():
    print("Testing S3 upload logic...")
    from driftwatch.utils.s3_client import S3Client
    with patch("boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        
        client = S3Client()
        client.upload_json("test.json", {"foo": "bar"})
        
        mock_s3.put_object.assert_called_once()
        args, kwargs = mock_s3.put_object.call_args
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["Key"] == "test.json"
        assert "foo" in kwargs["Body"]
        print("  - S3 upload_json call verified.")

if __name__ == "__main__":
    try:
        test_s3_client_initialization()
        test_s3_upload_logic()
        print("\nAll S3 integration tests passed (mocked)!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        sys.exit(1)
