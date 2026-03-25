"""
S3 storage integration for DriftWatch.
Handles uploading/downloading fingerprints and datasets.
"""

import os
import json
import boto3
import pandas as pd
from io import BytesIO, StringIO
from typing import Optional, Dict, Any, List

from driftwatch.utils.config import AWS_REGION, S3_DATA_BUCKET, IS_PROD
from driftwatch.utils.logger import get_logger

logger = get_logger("utils.s3")


class S3Client:
    """Wrapper for boto3 S3 operations."""

    def __init__(self):
        self.bucket = S3_DATA_BUCKET
        self.enabled = bool(self.bucket and AWS_REGION)
        self._client = None
        
        if self.enabled:
            try:
                # In production, boto3 uses IAM roles. In dev, uses local credentials.
                self._client = boto3.client("s3", region_name=AWS_REGION)
                logger.debug(f"S3 client initialized for bucket: {self.bucket}")
            except Exception as e:
                logger.warning(f"S3 client failed to initialize: {e}")
                self.enabled = False

    def upload_json(self, key: str, data: Dict[str, Any]) -> bool:
        """Upload dictionary as JSON to S3."""
        if not self.enabled:
            return False
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(data, default=str),
                ContentType="application/json"
            )
            logger.info(f"Uploaded JSON to s3://{self.bucket}/{key}")
            return True
        except Exception as e:
            logger.error(f"S3 upload failed ({key}): {e}")
            return False

    def download_json(self, key: str) -> Optional[Dict]:
        """Download JSON from S3 and return as dict."""
        if not self.enabled:
            return None
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except Exception as e:
            logger.error(f"S3 download failed ({key}): {e}")
            return None

    def upload_csv(self, key: str, df: pd.DataFrame) -> bool:
        """Upload DataFrame as CSV to S3."""
        if not self.enabled:
            return False
        try:
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=csv_buffer.getvalue(),
                ContentType="text/csv"
            )
            logger.info(f"Uploaded CSV to s3://{self.bucket}/{key}")
            return True
        except Exception as e:
            logger.error(f"S3 CSV upload failed ({key}): {e}")
            return False

    def download_csv(self, key: str) -> Optional[pd.DataFrame]:
        """Download CSV from S3 and return as DataFrame."""
        if not self.enabled:
            return None
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return pd.read_csv(response["Body"])
        except Exception as e:
            logger.error(f"S3 CSV download failed ({key}): {e}")
            return None

    def list_files(self, prefix: str = "") -> List[str]:
        """List files in bucket with given prefix."""
        if not self.enabled:
            return []
        try:
            response = self._client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception as e:
            logger.error(f"S3 list failed: {e}")
            return []


# Global instance
s3 = S3Client()
