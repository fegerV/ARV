"""
MindAR Marker Generator Service

This service generates .mind marker files using the MindAR offline compiler.
It uses the Node.js MindAR library with canvas support for server-side marker generation.
"""
import asyncio
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import structlog

from app.core.config import settings
from app.core.storage import get_storage_provider_instance

logger = structlog.get_logger()


class MindARGenerator:
    """Service for generating MindAR markers using the Node.js offline compiler"""

    def __init__(self):
        # Try to find mind-ar in node_modules
        project_root = Path(__file__).parent.parent.parent
        self.mindar_path = project_root / "node_modules" / "mind-ar"
        self.compiler_script = self._create_compiler_script()
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check if Node.js dependencies are available"""
        if not self.mindar_path.exists():
            logger.warning(
                "mindar_dependencies_missing",
                mindar_path=str(self.mindar_path),
                message="MindAR node_modules not found. Run 'npm install' to install dependencies. Marker generation will use fallback mode."
            )

    def _create_compiler_script(self) -> Path:
        """Get path to the Node.js compiler script"""
        # Prefer .mjs (ES6 module) over .js
        script_path_mjs = Path(__file__).parent / "mindar_compiler.mjs"
        script_path_js = Path(__file__).parent / "mindar_compiler.js"
        
        if script_path_mjs.exists():
            return script_path_mjs
        elif script_path_js.exists():
            logger.warning("using_legacy_compiler_js", 
                         message="Using .js compiler. Consider migrating to .mjs for ES6 module support")
            return script_path_js
        else:
            raise FileNotFoundError(f"MindAR compiler script not found: {script_path_js} or {script_path_mjs}")
    
    def validate_marker_file(self, marker_path: Path) -> Dict[str, Any]:
        """
        Validate marker file structure and content
        
        Args:
            marker_path: Path to .mind marker file
            
        Returns:
            Dictionary with validation results
        """
        warnings = []
        is_valid = True
        
        try:
            # Read and parse marker file
            with open(marker_path, 'r', encoding='utf-8') as f:
                marker_data = json.load(f)
            
            # Check basic structure
            if not isinstance(marker_data, dict):
                warnings.append("Marker file is not a valid JSON object")
                is_valid = False
                return {"is_valid": False, "warnings": warnings, "features_count": 0}
            
            # Check required fields
            if "version" not in marker_data:
                warnings.append("Missing 'version' field")
                is_valid = False
            
            if "type" not in marker_data:
                warnings.append("Missing 'type' field")
                is_valid = False
            
            if "trackingData" not in marker_data:
                warnings.append("Missing 'trackingData' field")
                is_valid = False
                return {"is_valid": False, "warnings": warnings, "features_count": 0}
            
            tracking_data = marker_data.get("trackingData", {})
            
            # Check features
            features = tracking_data.get("features", [])
            features_count = len(features) if isinstance(features, list) else 0
            
            if features_count == 0:
                warnings.append("Marker has no features - will not work for AR tracking")
                is_valid = False
            elif features_count < 10:
                warnings.append(f"Marker has very few features ({features_count}) - tracking may be unreliable")
            elif features_count < 50:
                warnings.append(f"Marker has few features ({features_count}) - tracking quality may be reduced")
            
            # Check descriptors
            descriptors = tracking_data.get("descriptors", [])
            descriptors_count = len(descriptors) if isinstance(descriptors, list) else 0
            
            if descriptors_count == 0 and features_count > 0:
                warnings.append("Marker has features but no descriptors - tracking may fail")
                is_valid = False
            elif descriptors_count != features_count:
                warnings.append(f"Descriptors count ({descriptors_count}) doesn't match features count ({features_count})")
            
            # Check image size
            image_size = tracking_data.get("imageSize", [])
            if not image_size or len(image_size) != 2:
                warnings.append("Missing or invalid imageSize in trackingData")
            else:
                width, height = image_size
                if width <= 0 or height <= 0:
                    warnings.append(f"Invalid image dimensions: {width}x{height}")
            
            # Check marker dimensions
            marker_width = marker_data.get("width", 0)
            marker_height = marker_data.get("height", 0)
            if marker_width <= 0 or marker_height <= 0:
                warnings.append(f"Invalid marker dimensions: {marker_width}x{marker_height}")
            
            return {
                "is_valid": is_valid,
                "warnings": warnings,
                "features_count": features_count,
                "descriptors_count": descriptors_count,
                "width": marker_width,
                "height": marker_height,
                "image_size": image_size
            }
            
        except json.JSONDecodeError as e:
            warnings.append(f"Marker file is not valid JSON: {str(e)}")
            return {"is_valid": False, "warnings": warnings, "features_count": 0}
        except Exception as e:
            warnings.append(f"Error validating marker file: {str(e)}")
            return {"is_valid": False, "warnings": warnings, "features_count": 0}

    async def generate_marker(
        self,
        image_path: Path,
        output_path: Path,
        max_features: int = None
    ) -> Dict[str, Any]:
        """
        Generate a MindAR marker file from an image
        
        Args:
            image_path: Path to input image file
            output_path: Path for output .mind file
            max_features: Maximum number of features to extract
            
        Returns:
            Dictionary with generation results
        """
        if max_features is None:
            max_features = settings.MINDAR_MAX_FEATURES
        
        log = logger.bind(
            image_path=str(image_path),
            output_path=str(output_path),
            max_features=max_features
        )
        
        log.info("mindar_marker_generation_started",
                 image_size_mb=round(image_path.stat().st_size / (1024 * 1024), 2) if image_path.exists() else 0)
        
        try:
            # Validate input image - try to resolve path if relative
            if not image_path.exists():
                # Try to resolve relative path from project root
                project_root = Path(__file__).parent.parent.parent
                resolved_path = project_root / image_path if not image_path.is_absolute() else image_path
                if resolved_path.exists():
                    image_path = resolved_path
                    log.info("image_path_resolved", 
                            original=str(image_path),
                            resolved=str(resolved_path))
                else:
                    error_msg = f"Input image not found: {image_path} (also tried: {resolved_path})"
                    log.error("input_image_not_found", 
                             image_path=str(image_path),
                             resolved_path=str(resolved_path),
                             project_root=str(project_root))
                    raise FileNotFoundError(error_msg)
            
            # Check image file size
            image_size = image_path.stat().st_size
            if image_size == 0:
                error_msg = "Input image file is empty"
                log.error("input_image_empty", image_path=str(image_path))
                raise ValueError(error_msg)
            
            log.info("input_image_validated", 
                    image_path=str(image_path),
                    image_size_bytes=image_size,
                    image_size_mb=round(image_size / (1024 * 1024), 2))
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            log.debug("output_directory_created", output_dir=str(output_path.parent))
            
            # Check if Node.js dependencies are available
            if not self.mindar_path.exists():
                error_msg = (
                    f"MindAR dependencies not found at {self.mindar_path}. "
                    "Please run 'npm install' to install mind-ar and canvas packages."
                )
                log.error("mindar_dependencies_missing", mindar_path=str(self.mindar_path))
                return {
                    "success": False,
                    "error": error_msg,
                    "error_type": "dependencies_missing"
                }
            
            # Run Node.js compiler script
            cmd = [
                "node",
                str(self.compiler_script),
                str(image_path.absolute()),
                str(output_path.absolute()),
                str(max_features)
            ]
            
            log.info("starting_nodejs_compiler",
                    command=" ".join(cmd),
                    max_features=max_features,
                    mindar_path_exists=self.mindar_path.exists())
            
            # Use project root as cwd (where node_modules should be)
            project_root = self.mindar_path.parent.parent
            cwd_path = str(project_root)
            
            log.debug("creating_subprocess",
                     command=" ".join(cmd),
                     cwd=cwd_path,
                     script_path=str(self.compiler_script))
            
            try:
                # Use subprocess.run in a thread for better Windows compatibility
                import subprocess
                
                def run_compiler():
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=cwd_path,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    return result
                
                # Run in thread to avoid blocking
                result = await asyncio.to_thread(run_compiler)
                log.debug("subprocess_completed", return_code=result.returncode)
                
                stdout_text = result.stdout if result.stdout else ""
                stderr_text = result.stderr if result.stderr else ""
                process_returncode = result.returncode
            except Exception as e:
                log.error("subprocess_execution_failed",
                         error=str(e),
                         error_type=type(e).__name__,
                         command=" ".join(cmd),
                         cwd=cwd_path,
                         exc_info=True)
                raise
            
            log.debug("compiler_process_completed",
                     return_code=process_returncode,
                     stdout_length=len(stdout_text),
                     stderr_length=len(stderr_text))
            
            if process_returncode != 0:
                error_msg = f"MindAR compilation failed (return code {process_returncode})"
                if stderr_text:
                    error_msg += f": {stderr_text[:200]}"
                
                log.error("mindar_compilation_failed", 
                         return_code=process_returncode,
                         stderr_preview=stderr_text[:500],
                         stdout_preview=stdout_text[:500],
                         full_stderr=stderr_text if len(stderr_text) < 1000 else None,
                         full_stdout=stdout_text if len(stdout_text) < 1000 else None)
                
                return {
                    "success": False,
                    "error": error_msg,
                    "return_code": process_returncode,
                    "stderr": stderr_text[:500] if stderr_text else None
                }
            
            # Check output file was created
            if not output_path.exists():
                error_msg = f"Marker file not created: {output_path}"
                log.error("mindar_output_missing", error=error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # Get file info
            file_size = output_path.stat().st_size
            
            # Try to parse result from stdout
            result_info = {}
            try:
                # Look for JSON-like output in the last line
                lines = stdout_text.strip().split('\n')
                for line in reversed(lines):
                    if line.startswith('{') and line.endswith('}'):
                        result_info = json.loads(line)
                        break
            except json.JSONDecodeError:
                pass
            
            # Log stdout for debugging if no JSON found
            if not result_info and stdout_text:
                log.debug("compiler_stdout_no_json", 
                         stdout_preview=stdout_text[-500:] if len(stdout_text) > 500 else stdout_text)
            
            # Validate marker file - check if it has features
            validation_result = self.validate_marker_file(output_path)
            
            # Get features count from validation (most reliable) or from stdout JSON
            features_count = validation_result.get("features_count", 0)
            if features_count == 0:
                features_count = result_info.get("features", 0)
            
            log.info("mindar_marker_generation_success",
                    file_size=file_size,
                    features_count=features_count,
                    is_valid=validation_result.get("is_valid", False),
                    validation_warnings=validation_result.get("warnings", []),
                    result_info=result_info,
                    stdout_preview=stdout_text[-200:] if stdout_text else None)
            
            if not validation_result.get("is_valid", False):
                log.warning("marker_validation_failed",
                           warnings=validation_result.get("warnings", []),
                           features_count=features_count,
                           stdout_preview=stdout_text[-300:] if stdout_text else None)
            
            return {
                "success": True,
                "marker_path": str(output_path),
                "file_size": file_size,
                "width": result_info.get("width") or validation_result.get("width"),
                "height": result_info.get("height") or validation_result.get("height"),
                "features": features_count,
                "is_valid": validation_result.get("is_valid", False),
                "validation_warnings": validation_result.get("warnings", [])
            }
            
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            log.error("mindar_generation_error", 
                     error=error_msg,
                     error_type=type(e).__name__,
                     exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "error_type": type(e).__name__
            }

    async def generate_and_upload_marker(
        self,
        ar_content_id: str,
        image_path: Path,
        max_features: int = None,
        storage_path: Path = None
    ) -> Dict[str, Any]:
        """
        Generate marker and upload to storage
        
        Args:
            ar_content_id: AR content ID
            image_path: Path to input image
            max_features: Maximum features to extract
            storage_path: Path where marker should be saved
            
        Returns:
            Dictionary with upload results
        """
        if not storage_path:
            raise ValueError("storage_path is required for marker generation")
        
        log = logger.bind(
            ar_content_id=ar_content_id,
            image_path=str(image_path),
            storage_path=str(storage_path)
        )
        
        # Determine output path
        marker_file_path = storage_path / "marker.mind"
        marker_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to generate real marker using Node.js compiler
        generation_result = await self.generate_marker(
            image_path=image_path,
            output_path=marker_file_path,
            max_features=max_features
        )
        
        log.info("generation_result_received",
                success=generation_result.get("success"),
                features=generation_result.get("features", 0),
                is_valid=generation_result.get("is_valid", False),
                error=generation_result.get("error"),
                ar_content_id=ar_content_id)
        
        # If generation failed, create a fallback marker with image dimensions
        if not generation_result.get("success"):
            error_detail = generation_result.get("error", "Unknown error")
            return_code = generation_result.get("return_code")
            
            log.warning("mindar_generation_failed_using_fallback", 
                       error=error_detail,
                       return_code=return_code,
                       ar_content_id=ar_content_id)
            
            # Get image dimensions for fallback
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    img_width, img_height = img.size
                    log.info("image_dimensions_retrieved", 
                            width=img_width, 
                            height=img_height)
            except Exception as e:
                log.warning("failed_to_get_image_dimensions", 
                           error=str(e),
                           using_defaults=True)
                img_width, img_height = 640, 480
            
            # Create fallback marker with correct dimensions
            import json
            import os
            
            fallback_marker_data = {
                "version": 2,
                "type": "image",
                "width": img_width,
                "height": img_height,
                "trackingData": {
                    "features": [],
                    "descriptors": [],
                    "imageSize": [img_width, img_height]
                }
            }
            
            with open(marker_file_path, 'w', encoding='utf-8') as f:
                json.dump(fallback_marker_data, f)
            
            file_size = marker_file_path.stat().st_size
            
            log.warning("fallback_marker_created",
                       width=img_width,
                       height=img_height,
                       file_size=file_size,
                       warning="Fallback marker has no features and will NOT work for AR tracking",
                       reason=error_detail)
            
            generation_result = {
                "success": True,
                "marker_path": str(marker_file_path),
                "file_size": file_size,
                "width": img_width,
                "height": img_height,
                "features": 0,
                "is_valid": False,
                "validation_warnings": [
                    "Fallback marker created - no features extracted",
                    f"Original error: {error_detail}"
                ]
            }
        
        # Build public URL
        from app.utils.ar_content import build_public_url
        marker_url = build_public_url(marker_file_path)
        
        result = {
            "success": generation_result.get("success", True),
            "marker_path": str(marker_file_path),
            "file_size": generation_result.get("file_size", 0),
            "width": generation_result.get("width"),
            "height": generation_result.get("height"),
            "features": generation_result.get("features", 0),
            "marker_url": marker_url,
            "storage_path": str(marker_file_path),
            "is_valid": generation_result.get("is_valid", False),
            "validation_warnings": generation_result.get("validation_warnings", [])
        }
        
        # Log final result with validation status
        if result.get("is_valid") is True:
            log.info("marker_generated_and_validated",
                    marker_url=marker_url,
                    file_size=result["file_size"],
                    features=result["features"],
                    width=result["width"],
                    height=result["height"])
        else:
            log.warning("marker_generated_but_invalid",
                       marker_url=marker_url,
                       file_size=result["file_size"],
                       features=result["features"],
                       warnings=result["validation_warnings"],
                       message="Marker was created but may not work for AR tracking")
        
        return result


# Singleton instance
mindar_generator = MindARGenerator()
