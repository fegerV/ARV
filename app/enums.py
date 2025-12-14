# Enums for the application

from enum import Enum


class CompanyStatus(str, Enum):
    """Company status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProjectStatus(str, Enum):
    """Project status enum"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class ArContentStatus(str, Enum):
    """AR Content status enum"""
    PENDING = "pending"
    ACTIVE = "active"
    ARCHIVED = "archived"


class VideoStatus(str, Enum):
    """Video status enum"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"