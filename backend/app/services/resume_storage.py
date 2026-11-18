import os
import uuid
import datetime
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
import io
import jwt
from app.core.config import settings

class BaseStorageBackend(ABC):
    @abstractmethod
    def save(self, content_bytes: bytes, original_filename: str, user_id: int) -> Tuple[str, int]:
        """Saves file bytes and returns (storage_path_or_key, file_size)."""
        pass

    @abstractmethod
    def delete(self, storage_path: str) -> bool:
        """Deletes file from storage."""
        pass

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """Checks if file exists in storage."""
        pass

    @abstractmethod
    def get_download_response(self, storage_path: str, filename: str):
        """Returns an HTTP response for file download."""
        pass

    @abstractmethod
    def read(self, storage_path: str) -> bytes:
        """Reads file bytes from storage."""
        pass


class LocalStorageBackend(BaseStorageBackend):
    def __init__(self, upload_dir: Optional[str] = None):
        self.upload_dir = upload_dir or settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    def save(self, content_bytes: bytes, original_filename: str, user_id: int) -> Tuple[str, int]:
        ext = os.path.splitext(original_filename)[1].lower()
        safe_filename = f"resume_{user_id}_{uuid.uuid4().hex[:12]}{ext}"
        storage_path = os.path.join(self.upload_dir, safe_filename)

        with open(storage_path, "wb") as f:
            f.write(content_bytes)

        return storage_path, len(content_bytes)

    def delete(self, storage_path: str) -> bool:
        if storage_path and os.path.exists(storage_path):
            try:
                os.remove(storage_path)
                return True
            except OSError:
                return False
        return False

    def exists(self, storage_path: str) -> bool:
        return bool(storage_path and os.path.exists(storage_path))

    def get_download_response(self, storage_path: str, filename: str):
        if not self.exists(storage_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File on disk not found")
        return FileResponse(
            path=storage_path,
            filename=filename,
            media_type="application/octet-stream"
        )

    def read(self, storage_path: str) -> bytes:
        if not self.exists(storage_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File on disk not found")
        with open(storage_path, "rb") as f:
            return f.read()


class S3StorageBackend(BaseStorageBackend):
    """
    S3-compatible Cloud Storage Backend.
    Supports AWS S3, Cloudflare R2, MinIO, and other S3-compliant object storage.
    """
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.region_name = settings.S3_REGION_NAME
        self.access_key = settings.S3_ACCESS_KEY_ID
        self.secret_key = settings.S3_SECRET_ACCESS_KEY
        self.force_path_style = settings.S3_FORCE_PATH_STYLE
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
                s3_config = Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path" if self.force_path_style else "auto"}
                )
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url or None,
                    region_name=self.region_name,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    config=s3_config
                )
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="boto3 library is required for S3StorageBackend. Please install boto3."
                )
        return self._client

    def _parse_key(self, storage_path: str) -> str:
        if storage_path.startswith("s3://"):
            parts = storage_path[5:].split("/", 1)
            return parts[1] if len(parts) > 1 else parts[0]
        return storage_path

    def save(self, content_bytes: bytes, original_filename: str, user_id: int) -> Tuple[str, int]:
        ext = os.path.splitext(original_filename)[1].lower()
        key = f"resumes/user_{user_id}/resume_{user_id}_{uuid.uuid4().hex[:12]}{ext}"
        client = self._get_client()
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content_bytes,
            ContentType="application/pdf" if ext == ".pdf" else "application/octet-stream"
        )
        storage_path = f"s3://{self.bucket_name}/{key}"
        return storage_path, len(content_bytes)

    def delete(self, storage_path: str) -> bool:
        try:
            key = self._parse_key(storage_path)
            client = self._get_client()
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def exists(self, storage_path: str) -> bool:
        try:
            key = self._parse_key(storage_path)
            client = self._get_client()
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def get_download_response(self, storage_path: str, filename: str):
        try:
            key = self._parse_key(storage_path)
            client = self._get_client()
            obj = client.get_object(Bucket=self.bucket_name, Key=key)
            stream = io.BytesIO(obj["Body"].read())
            return StreamingResponse(
                stream,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File in cloud storage not found")

    def read(self, storage_path: str) -> bytes:
        try:
            key = self._parse_key(storage_path)
            client = self._get_client()
            obj = client.get_object(Bucket=self.bucket_name, Key=key)
            return obj["Body"].read()
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File in cloud storage not found")


def get_storage_backend() -> BaseStorageBackend:
    if settings.STORAGE_BACKEND.lower() == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()


class ResumeStorageService:
    @staticmethod
    def ensure_upload_dir():
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    @classmethod
    def save_resume(cls, file: UploadFile, user_id: int) -> Tuple[str, str, int]:
        # 1. Content-Type and extension validation
        allowed_extensions = {".pdf", ".docx", ".txt"}
        original_name = file.filename or "resume.pdf"
        ext = os.path.splitext(original_name)[1].lower()

        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext}'. Allowed types: PDF, DOCX, TXT."
            )

        # 2. File size and magic bytes content validation (PRD 9.2)
        content_header = file.file.read(512)
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)

        if size > settings.MAX_RESUME_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {settings.MAX_RESUME_SIZE_BYTES // (1024 * 1024)}MB."
            )

        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        # Magic bytes content validation
        if ext == ".pdf" and not content_header.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Invalid PDF file content")
        elif ext == ".docx" and not content_header.startswith(b"PK\x03\x04"):
            raise HTTPException(status_code=400, detail="Invalid DOCX file content")
        elif ext == ".txt":
            try:
                content_header.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Invalid plain text file encoding")

        # 3. Read full content and save through active pluggable storage backend
        full_content = file.file.read()
        backend = get_storage_backend()
        storage_path, stored_size = backend.save(full_content, original_name, user_id)

        return original_name, storage_path, stored_size

    @classmethod
    def generate_signed_download_token(cls, user_id: int, filename: str) -> str:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
        payload = {
            "sub": str(user_id),
            "filename": filename,
            "exp": expire,
            "type": "resume_download"
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @classmethod
    def verify_download_token(cls, token: str) -> Tuple[int, str]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "resume_download":
                raise HTTPException(status_code=403, detail="Invalid token type")
            return int(payload["sub"]), payload["filename"]
        except Exception:
            raise HTTPException(status_code=403, detail="Download link has expired or is invalid")

    @classmethod
    def delete_resume_file(cls, storage_path: Optional[str]):
        if not storage_path:
            return
        if storage_path.startswith("s3://"):
            backend = S3StorageBackend()
            backend.delete(storage_path)
        else:
            local_backend = LocalStorageBackend()
            local_backend.delete(storage_path)

    @classmethod
    def get_download_response(cls, storage_path: str, filename: str):
        if storage_path.startswith("s3://"):
            backend = S3StorageBackend()
            return backend.get_download_response(storage_path, filename)
        else:
            local_backend = LocalStorageBackend()
            return local_backend.get_download_response(storage_path, filename)

    @classmethod
    def read_resume_content(cls, storage_path: str) -> bytes:
        if storage_path.startswith("s3://"):
            backend = S3StorageBackend()
            return backend.read(storage_path)
        else:
            local_backend = LocalStorageBackend()
            return local_backend.read(storage_path)
