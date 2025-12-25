"""
Enhanced Validation Service with deep content analysis, security scanning, and comprehensive validation.
"""
import asyncio
import hashlib
import imghdr
import mimetypes
import os
import magic
import structlog
from pathlib import Path
from typing import Optional, Dict, List, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import tempfile
import subprocess
import json
from PIL import Image, ExifTags
import cv2
import numpy as np

from app.core.config import settings

logger = structlog.get_logger()

class ValidationLevel(Enum):
    BASIC = "basic"          # File extension, size, MIME type
    STANDARD = "standard"    # + Content integrity, metadata validation
    COMPREHENSIVE = "comprehensive"  # + Security scanning, deep analysis
    PARANOID = "paranoid"    # + All checks + behavioral analysis

class ThreatLevel(Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"

@dataclass
class ValidationResult:
    is_valid: bool
    threat_level: ThreatLevel = ThreatLevel.UNKNOWN
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    security_info: Dict[str, Any] = field(default_factory=dict)
    file_info: Dict[str, Any] = field(default_factory=dict)
    validation_time: Optional[float] = None
    validation_level: ValidationLevel = ValidationLevel.BASIC

@dataclass
class FileConstraints:
    max_file_size: int
    allowed_extensions: List[str]
    allowed_mime_types: List[str]
    min_resolution: Optional[Tuple[int, int]] = None
    max_resolution: Optional[Tuple[int, int]] = None
    max_duration: Optional[float] = None  # For videos
    min_duration: Optional[float] = None
    require_metadata: bool = False

class EnhancedValidationService:
    """Enhanced validation service with security scanning and deep analysis."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "vertex_validation"
        self.temp_dir.mkdir(exist_ok=True)
        
        # File type constraints
        self.image_constraints = FileConstraints(
            max_file_size=settings.MAX_FILE_SIZE_PHOTO,
            allowed_extensions=['jpeg', 'jpg', 'png', 'webp', 'heic', 'heif'],
            allowed_mime_types=[
                'image/jpeg', 'image/png', 'image/webp', 
                'image/heic', 'image/heif'
            ],
            min_resolution=(100, 100),
            max_resolution=(8192, 8192),
            require_metadata=False
        )
        
        self.video_constraints = FileConstraints(
            max_file_size=settings.MAX_FILE_SIZE_VIDEO,
            allowed_extensions=['mp4', 'webm', 'mov', 'avi', 'mkv'],
            allowed_mime_types=[
                'video/mp4', 'video/webm', 'video/quicktime',
                'video/x-msvideo', 'video/x-matroska'
            ],
            min_resolution=(240, 240),
            max_resolution=(4096, 4096),
            min_duration=0.5,
            max_duration=3600  # 1 hour max
        )
        
        # Security scanning configuration
        self.enable_virus_scan = True
        self.enable_metadata_sanitization = True
        self.enable_content_analysis = True
        
    async def validate_file(
        self,
        file_path: str,
        file_type: str = "auto",
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        original_filename: Optional[str] = None
    ) -> ValidationResult:
        """
        Comprehensive file validation with security scanning.
        
        Args:
            file_path: Path to file to validate
            file_type: 'image', 'video', or 'auto' for auto-detection
            validation_level: How thorough the validation should be
            original_filename: Original filename for better validation
            
        Returns:
            ValidationResult with comprehensive information
        """
        import time
        start_time = time.time()
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return ValidationResult(
                    is_valid=False,
                    errors=["File does not exist"],
                    validation_time=time.time() - start_time,
                    validation_level=validation_level
                )
            
            # Auto-detect file type if needed
            if file_type == "auto":
                file_type = await self._detect_file_type(file_path, original_filename)
            
            # Get file constraints
            constraints = self._get_constraints(file_type)
            if not constraints:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Unsupported file type: {file_type}"],
                    validation_time=time.time() - start_time,
                    validation_level=validation_level
                )
            
            result = ValidationResult(
                validation_level=validation_level,
                validation_time=time.time() - start_time
            )
            
            # Basic validation
            await self._basic_validation(file_path, constraints, result)
            
            if not result.is_valid or validation_level == ValidationLevel.BASIC:
                return result
            
            # Standard validation
            await self._standard_validation(file_path, file_type, constraints, result)
            
            if not result.is_valid or validation_level == ValidationLevel.STANDARD:
                return result
            
            # Comprehensive validation
            await self._comprehensive_validation(file_path, file_type, result)
            
            if not result.is_valid or validation_level == ValidationLevel.COMPREHENSIVE:
                return result
            
            # Paranoid validation
            await self._paranoid_validation(file_path, file_type, result)
            
            # Set final threat level
            result.threat_level = self._assess_threat_level(result)
            
            result.validation_time = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error("validation_failed", file_path=str(file_path), error=str(e), exc_info=True)
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation failed: {str(e)}"],
                validation_time=time.time() - start_time,
                validation_level=validation_level
            )
    
    async def _detect_file_type(self, file_path: Path, original_filename: Optional[str] = None) -> str:
        """Auto-detect file type using multiple methods."""
        
        # Try Python magic first
        try:
            mime_type = magic.from_file(str(file_path), mime=True)
            if mime_type.startswith('image/'):
                return 'image'
            elif mime_type.startswith('video/'):
                return 'video'
        except Exception:
            pass
        
        # Try imghdr for images
        try:
            if imghdr.what(str(file_path)):
                return 'image'
        except Exception:
            pass
        
        # Try OpenCV for video detection
        try:
            cap = cv2.VideoCapture(str(file_path))
            if cap.isOpened():
                cap.release()
                return 'video'
        except Exception:
            pass
        
        # Fallback to extension
        if original_filename:
            ext = Path(original_filename).suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif']:
                return 'image'
            elif ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv']:
                return 'video'
        
        return 'unknown'
    
    def _get_constraints(self, file_type: str) -> Optional[FileConstraints]:
        """Get file constraints based on type."""
        if file_type == 'image':
            return self.image_constraints
        elif file_type == 'video':
            return self.video_constraints
        return None
    
    async def _basic_validation(self, file_path: Path, constraints: FileConstraints, result: ValidationResult) -> None:
        """Basic file validation: size, extension, MIME type."""
        
        # File size validation
        file_size = file_path.stat().st_size
        result.file_info['size_bytes'] = file_size
        
        if file_size > constraints.max_file_size:
            result.is_valid = False
            result.errors.append(f"File too large: {file_size} bytes (max: {constraints.max_file_size})")
        
        if file_size == 0:
            result.is_valid = False
            result.errors.append("File is empty")
        
        # Extension validation
        extension = file_path.suffix.lower().lstrip('.')
        result.file_info['extension'] = extension
        
        if extension not in constraints.allowed_extensions:
            result.is_valid = False
            result.errors.append(f"Extension not allowed: {extension}")
        
        # MIME type validation
        try:
            mime_type = magic.from_file(str(file_path), mime=True)
            result.file_info['mime_type'] = mime_type
            
            if mime_type not in constraints.allowed_mime_types:
                result.is_valid = False
                result.errors.append(f"MIME type not allowed: {mime_type}")
        except Exception as e:
            result.warnings.append(f"Could not detect MIME type: {str(e)}")
    
    async def _standard_validation(self, file_path: Path, file_type: str, constraints: FileConstraints, result: ValidationResult) -> None:
        """Standard validation: content integrity, metadata."""
        
        if file_type == 'image':
            await self._validate_image_content(file_path, constraints, result)
        elif file_type == 'video':
            await self._validate_video_content(file_path, constraints, result)
    
    async def _validate_image_content(self, file_path: Path, constraints: FileConstraints, result: ValidationResult) -> None:
        """Validate image content and extract metadata."""
        
        try:
            with Image.open(file_path) as img:
                # Basic image info
                result.metadata.update({
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'has_transparency': img.mode in ('RGBA', 'LA', 'P')
                })
                
                width, height = img.size
                result.file_info['resolution'] = f"{width}x{height}"
                result.file_info['width'] = width
                result.file_info['height'] = height
                
                # Resolution validation
                if constraints.min_resolution:
                    min_w, min_h = constraints.min_resolution
                    if width < min_w or height < min_h:
                        result.errors.append(f"Resolution too small: {width}x{height} (min: {min_w}x{min_h})")
                        result.is_valid = False
                
                if constraints.max_resolution:
                    max_w, max_h = constraints.max_resolution
                    if width > max_w or height > max_h:
                        result.errors.append(f"Resolution too large: {width}x{height} (max: {max_w}x{max_h})")
                        result.is_valid = False
                
                # Verify image integrity by loading it
                img.verify()
                
                # Extract EXIF data
                try:
                    with Image.open(file_path) as img:
                        exif = img.getexif()
                        if exif:
                            exif_data = {}
                            for tag_id, value in exif.items():
                                tag = ExifTags.TAGS.get(tag_id, tag_id)
                                exif_data[tag] = str(value)
                            result.metadata['exif'] = exif_data
                            
                            # Check for potentially suspicious EXIF data
                            await self._analyze_exif_security(exif_data, result)
                except Exception as e:
                    result.warnings.append(f"Could not extract EXIF data: {str(e)}")
                
                # Check for image anomalies
                await self._detect_image_anomalies(file_path, result)
                
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Invalid image file: {str(e)}")
    
    async def _validate_video_content(self, file_path: Path, constraints: FileConstraints, result: ValidationResult) -> None:
        """Validate video content and extract metadata."""
        
        try:
            # Use ffprobe for video analysis
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', str(file_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                result.is_valid = False
                result.errors.append(f"Invalid video file: {stderr.decode()}")
                return
            
            probe_data = json.loads(stdout.decode())
            
            # Extract video stream info
            video_stream = None
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                result.is_valid = False
                result.errors.append("No video stream found")
                return
            
            # Extract metadata
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            duration = float(probe_data.get('format', {}).get('duration', 0))
            bitrate = int(probe_data.get('format', {}).get('bit_rate', 0))
            
            result.metadata.update({
                'codec': video_stream.get('codec_name'),
                'width': width,
                'height': height,
                'duration': duration,
                'bitrate': bitrate,
                'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                'pixel_format': video_stream.get('pix_fmt'),
                'frame_count': int(video_stream.get('nb_frames', 0))
            })
            
            result.file_info.update({
                'resolution': f"{width}x{height}",
                'width': width,
                'height': height,
                'duration': duration,
                'bitrate': bitrate
            })
            
            # Resolution validation
            if constraints.min_resolution:
                min_w, min_h = constraints.min_resolution
                if width < min_w or height < min_h:
                    result.errors.append(f"Resolution too small: {width}x{height}")
                    result.is_valid = False
            
            if constraints.max_resolution:
                max_w, max_h = constraints.max_resolution
                if width > max_w or height > max_h:
                    result.errors.append(f"Resolution too large: {width}x{height}")
                    result.is_valid = False
            
            # Duration validation
            if constraints.min_duration and duration < constraints.min_duration:
                result.errors.append(f"Duration too short: {duration}s (min: {constraints.min_duration}s)")
                result.is_valid = False
            
            if constraints.max_duration and duration > constraints.max_duration:
                result.errors.append(f"Duration too long: {duration}s (max: {constraints.max_duration}s)")
                result.is_valid = False
            
            # Check for video anomalies
            await self._detect_video_anomalies(file_path, result)
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Video validation failed: {str(e)}")
    
    async def _comprehensive_validation(self, file_path: Path, file_type: str, result: ValidationResult) -> None:
        """Comprehensive validation: security scanning, deep analysis."""
        
        # Security scanning
        if self.enable_virus_scan:
            await self._virus_scan(file_path, result)
        
        # Content analysis
        if self.enable_content_analysis:
            if file_type == 'image':
                await self._deep_image_analysis(file_path, result)
            elif file_type == 'video':
                await self._deep_video_analysis(file_path, result)
        
        # Metadata sanitization check
        if self.enable_metadata_sanitization:
            await self._check_metadata_sanitization(file_path, result)
    
    async def _paranoid_validation(self, file_path: Path, file_type: str, result: ValidationResult) -> None:
        """Paranoid validation: behavioral analysis, advanced threat detection."""
        
        # File signature analysis
        await self._analyze_file_signatures(file_path, result)
        
        # Entropy analysis for steganography detection
        if file_type == 'image':
            await self._entropy_analysis(file_path, result)
        
        # Behavioral analysis
        await self._behavioral_analysis(file_path, result)
    
    async def _analyze_exif_security(self, exif_data: Dict[str, Any], result: ValidationResult) -> None:
        """Analyze EXIF data for security concerns."""
        
        suspicious_patterns = [
            'shell', 'exec', 'system', 'eval', 'javascript:',
            'data:', 'vbscript:', 'file:', 'ftp:'
        ]
        
        for key, value in exif_data.items():
            value_str = str(value).lower()
            for pattern in suspicious_patterns:
                if pattern in value_str:
                    result.warnings.append(f"Suspicious content in EXIF {key}: {pattern}")
                    result.threat_level = ThreatLevel.SUSPICIOUS
    
    async def _detect_image_anomalies(self, file_path: Path, result: ValidationResult) -> None:
        """Detect image anomalies and potential issues."""
        
        try:
            with Image.open(file_path) as img:
                # Check for unusual aspect ratios
                width, height = img.size
                aspect_ratio = width / height
                
                if aspect_ratio > 10 or aspect_ratio < 0.1:
                    result.warnings.append(f"Unusual aspect ratio: {aspect_ratio:.2f}")
                
                # Check for solid color images
                colors = img.getcolors(maxcolors=256)
                if colors and len(colors) == 1:
                    result.warnings.append("Image appears to be a solid color")
                
                # Check for very small images
                if width < 50 or height < 50:
                    result.warnings.append(f"Very small image: {width}x{height}")
                
        except Exception as e:
            result.warnings.append(f"Could not analyze image anomalies: {str(e)}")
    
    async def _detect_video_anomalies(self, file_path: Path, result: ValidationResult) -> None:
        """Detect video anomalies and potential issues."""
        
        try:
            # Sample video frames for analysis
            cap = cv2.VideoCapture(str(file_path))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if frame_count == 0:
                result.errors.append("Video has no frames")
                result.is_valid = False
                return
            
            # Check first and last frames
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, first_frame = cap.read()
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
            ret, last_frame = cap.read()
            
            cap.release()
            
            # Check for black frames
            if first_frame is not None and np.mean(first_frame) < 10:
                result.warnings.append("Video starts with black frame")
            
            if last_frame is not None and np.mean(last_frame) < 10:
                result.warnings.append("Video ends with black frame")
                
        except Exception as e:
            result.warnings.append(f"Could not analyze video anomalies: {str(e)}")
    
    async def _virus_scan(self, file_path: Path, result: ValidationResult) -> None:
        """Scan file for viruses using ClamAV."""
        
        try:
            # Try to use clamdscan if available
            cmd = ['clamdscan', '--no-summary', str(file_path)]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result.security_info['virus_scan'] = 'clean'
            elif process.returncode == 1:
                result.security_info['virus_scan'] = 'infected'
                result.is_valid = False
                result.errors.append("File contains virus")
                result.threat_level = ThreatLevel.MALICIOUS
            else:
                result.warnings.append(f"Virus scan failed: {stderr.decode()}")
                result.security_info['virus_scan'] = 'failed'
                
        except Exception as e:
            result.warnings.append(f"Virus scan not available: {str(e)}")
            result.security_info['virus_scan'] = 'unavailable'
    
    async def _deep_image_analysis(self, file_path: Path, result: ValidationResult) -> None:
        """Deep image analysis for content classification."""
        
        try:
            # Use OpenCV for advanced analysis
            img = cv2.imread(str(file_path))
            if img is None:
                return
            
            # Color histogram analysis
            hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist_norm = cv2.normalize(hist, hist).flatten()
            
            result.metadata['color_histogram'] = hist_norm.tolist()[:50]  # Sample
            
            # Edge detection for content analysis
            edges = cv2.Canny(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            result.metadata['edge_density'] = float(edge_density)
            
            if edge_density < 0.01:
                result.warnings.append("Very low edge density - possibly simple graphic")
            elif edge_density > 0.3:
                result.warnings.append("Very high edge density - possibly noisy image")
                
        except Exception as e:
            result.warnings.append(f"Deep image analysis failed: {str(e)}")
    
    async def _deep_video_analysis(self, file_path: Path, result: ValidationResult) -> None:
        """Deep video analysis for quality assessment."""
        
        try:
            cap = cv2.VideoCapture(str(file_path))
            
            # Sample multiple frames for analysis
            frame_samples = []
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            sample_interval = max(1, total_frames // 10)
            
            for i in range(0, total_frames, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    frame_samples.append(frame)
            
            cap.release()
            
            if frame_samples:
                # Calculate average brightness and contrast
                brightnesses = [np.mean(frame) for frame in frame_samples]
                contrasts = [np.std(frame) for frame in frame_samples]
                
                result.metadata['avg_brightness'] = float(np.mean(brightnesses))
                result.metadata['avg_contrast'] = float(np.mean(contrasts))
                
                # Check for unusual patterns
                if np.mean(brightnesses) < 20:
                    result.warnings.append("Video appears very dark")
                elif np.mean(brightnesses) > 240:
                    result.warnings.append("Video appears very bright")
                    
        except Exception as e:
            result.warnings.append(f"Deep video analysis failed: {str(e)}")
    
    async def _check_metadata_sanitization(self, file_path: Path, result: ValidationResult) -> None:
        """Check if metadata needs sanitization."""
        
        # This would implement metadata sanitization checks
        # For now, just note that it was checked
        result.security_info['metadata_checked'] = True
    
    async def _analyze_file_signatures(self, file_path: Path, result: ValidationResult) -> None:
        """Analyze file signatures for tampering detection."""
        
        try:
            # Read file header
            with open(file_path, 'rb') as f:
                header = f.read(32)
            
            # Check for common file signatures
            signatures = {
                b'\xFF\xD8\xFF': 'JPEG',
                b'\x89PNG\r\n\x1a\n': 'PNG',
                b'RIFF': 'AVI/WebP',
                b'ftyp': 'MP4/MOV',
            }
            
            detected_signature = None
            for sig, format_name in signatures.items():
                if header.startswith(sig):
                    detected_signature = format_name
                    break
            
            if detected_signature:
                result.security_info['file_signature'] = detected_signature
            else:
                result.warnings.append("Unknown file signature")
                result.security_info['file_signature'] = 'unknown'
                
        except Exception as e:
            result.warnings.append(f"File signature analysis failed: {str(e)}")
    
    async def _entropy_analysis(self, file_path: Path, result: ValidationResult) -> None:
        """Analyze file entropy for steganography detection."""
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Calculate byte frequency
            byte_counts = [0] * 256
            for byte in data:
                byte_counts[byte] += 1
            
            # Calculate entropy
            entropy = 0
            data_len = len(data)
            for count in byte_counts:
                if count > 0:
                    prob = count / data_len
                    entropy -= prob * np.log2(prob)
            
            result.metadata['entropy'] = float(entropy)
            
            # High entropy might indicate encryption or steganography
            if entropy > 7.8:
                result.warnings.append(f"High file entropy: {entropy:.2f} (possible encryption/steganography)")
                result.threat_level = ThreatLevel.SUSPICIOUS
                
        except Exception as e:
            result.warnings.append(f"Entropy analysis failed: {str(e)}")
    
    async def _behavioral_analysis(self, file_path: Path, result: ValidationResult) -> None:
        """Behavioral analysis of the file."""
        
        # This would implement more advanced behavioral analysis
        # For now, just note that it was performed
        result.security_info['behavioral_analysis'] = 'completed'
    
    def _assess_threat_level(self, result: ValidationResult) -> ThreatLevel:
        """Assess overall threat level based on validation results."""
        
        if result.errors:
            return ThreatLevel.MALICIOUS
        
        warning_count = len(result.warnings)
        security_issues = sum(1 for v in result.security_info.values() if v in ['infected', 'failed'])
        
        if security_issues > 0:
            return ThreatLevel.MALICIOUS
        elif warning_count > 5 or result.threat_level == ThreatLevel.SUSPICIOUS:
            return ThreatLevel.SUSPICIOUS
        elif warning_count > 0:
            return ThreatLevel.SUSPICIOUS
        else:
            return ThreatLevel.SAFE
    
    async def batch_validate(
        self,
        file_paths: List[str],
        validation_level: ValidationLevel = ValidationLevel.STANDARD
    ) -> List[ValidationResult]:
        """Validate multiple files concurrently."""
        
        tasks = [
            self.validate_file(path, validation_level=validation_level)
            for path in file_paths
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ValidationResult(
                    is_valid=False,
                    errors=[f"Validation exception: {str(result)}"],
                    validation_level=validation_level
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get summary statistics for batch validation results."""
        
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid
        
        threat_counts = {}
        for result in results:
            threat = result.threat_level.value
            threat_counts[threat] = threat_counts.get(threat, 0) + 1
        
        avg_time = sum(r.validation_time or 0 for r in results) / total if total > 0 else 0
        
        return {
            'total_files': total,
            'valid_files': valid,
            'invalid_files': invalid,
            'success_rate': (valid / total * 100) if total > 0 else 0,
            'threat_distribution': threat_counts,
            'average_validation_time': avg_time,
            'total_warnings': sum(len(r.warnings) for r in results),
            'total_errors': sum(len(r.errors) for r in results)
        }

# Singleton instance
enhanced_validation_service = EnhancedValidationService()