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
        self.mindar_path = Path(__file__).parent.parent.parent / "node_modules" / "mind-ar"
        self.compiler_script = self._create_compiler_script()

    def _create_compiler_script(self) -> Path:
        """Get path to the Node.js compiler script"""
        script_path = Path(__file__).parent / "mindar_compiler.js"
        if not script_path.exists():
            raise FileNotFoundError(f"MindAR compiler script not found: {script_path}")
        return script_path

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
        
        log.info("mindar_marker_generation_started")
        
        try:
            # Validate input image
            if not image_path.exists():
                raise FileNotFoundError(f"Input image not found: {image_path}")
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Run Node.js compiler script
            cmd = [
                "node",
                str(self.compiler_script),
                str(image_path.absolute()),
                str(output_path.absolute()),
                str(max_features)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.mindar_path)
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""
            
            if process.returncode != 0:
                log.error("mindar_compilation_failed", 
                         return_code=process.returncode,
                         stderr=stderr_text,
                         stdout=stdout_text)
                return {
                    "success": False,
                    "error": f"MindAR compilation failed: {stderr_text}",
                    "return_code": process.returncode
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
            
            log.info("mindar_marker_generation_success",
                    file_size=file_size,
                    result_info=result_info)
            
            return {
                "success": True,
                "marker_path": str(output_path),
                "file_size": file_size,
                "width": result_info.get("width"),
                "height": result_info.get("height"),
                "features": result_info.get("features", 0)
            }
            
        except Exception as e:
            log.error("mindar_generation_error", error=str(e), exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_and_upload_marker(
        self,
        ar_content_id: str,
        image_path: Path,
        max_features: int = None
    ) -> Dict[str, Any]:
        """
        Generate marker and upload to storage
        
        Args:
            ar_content_id: AR content ID
            image_path: Path to input image
            max_features: Maximum features to extract
            
        Returns:
            Dictionary with upload results
        """
        # Generate marker to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mind', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Generate marker
            result = await self.generate_marker(
                image_path=image_path,
                output_path=temp_path,
                max_features=max_features
            )
            
            if not result["success"]:
                return result
            
            # Upload to storage
            storage_provider = get_storage_provider_instance()
            marker_storage_path = f"markers/{ar_content_id}/targets.mind"
            
            marker_url = await storage_provider.save_file(
                source_path=str(temp_path),
                destination_path=marker_storage_path
            )
            
            result.update({
                "marker_url": marker_url,
                "storage_path": marker_storage_path
            })
            
            return result
            
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()


# Singleton instance
mindar_generator = MindARGenerator()
