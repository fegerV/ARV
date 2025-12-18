"""
CPU-intensive processing tasks.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from fastapi import BackgroundTasks

from app.core.config import settings
from app.core.storage import get_storage_provider
from . import run_background_task, run_in_threadpool

logger = logging.getLogger(__name__)

# Ensure OpenCV is built with CUDA if available
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    try:
        cv2.cuda.setDevice(0)
        logger.info("CUDA is available and will be used for image processing")
    except Exception as e:
        logger.warning(f"CUDA device found but could not be initialized: {e}")


async def process_image(
    background_tasks: BackgroundTasks,
    image_path: str,
    output_path: str,
    operations: List[Dict[str, Any]],
    **kwargs
) -> str:
    """
    Process an image in the background.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        image_path: Path to the source image
        output_path: Path to save the processed image
        operations: List of image processing operations to apply
        **kwargs: Additional arguments for processing
        
    Returns:
        Path to the processed image
    """
    # Run the actual processing in a background thread
    await run_background_task(
        background_tasks,
        _process_image,
        image_path=image_path,
        output_path=output_path,
        operations=operations,
        **kwargs
    )
    
    logger.info("image_processing_queued", 
               source=image_path, 
               target=output_path,
               operations=len(operations))
    
    return output_path


def _process_image(
    image_path: str,
    output_path: str,
    operations: List[Dict[str, Any]],
    **kwargs
) -> str:
    """
    Process an image (runs in a background thread).
    
    Args:
        image_path: Path to the source image
        output_path: Path to save the processed image
        operations: List of image processing operations to apply
        **kwargs: Additional arguments for processing
        
    Returns:
        Path to the processed image
    """
    logger.info("starting_image_processing", 
               source=image_path, 
               target=output_path,
               operations=len(operations))
    
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image from {image_path}")
        
        # Apply each operation
        for op in operations:
            op_type = op.get('type')
            params = op.get('params', {})
            
            if op_type == 'resize':
                img = _resize_image(img, **params)
            elif op_type == 'crop':
                img = _crop_image(img, **params)
            elif op_type == 'grayscale':
                img = _convert_to_grayscale(img)
            elif op_type == 'blur':
                img = _apply_blur(img, **params)
            elif op_type == 'threshold':
                img = _apply_threshold(img, **params)
            elif op_type == 'rotate':
                img = _rotate_image(img, **params)
            # Add more operations as needed
        
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Save the processed image
        cv2.imwrite(output_path, img)
        logger.info("image_processing_completed", output_path=output_path)
        
        return output_path
    except Exception as e:
        logger.error("image_processing_failed", 
                    source=image_path,
                    error=str(e),
                    exc_info=True)
        raise


def _resize_image(img: np.ndarray, width: int = None, height: int = None, 
                 keep_aspect_ratio: bool = True) -> np.ndarray:
    """Resize an image."""
    if width is None and height is None:
        return img
    
    h, w = img.shape[:2]
    
    if keep_aspect_ratio:
        if width is not None and height is not None:
            # Use the smaller dimension to maintain aspect ratio
            ratio = min(width / w, height / h)
            new_w, new_h = int(w * ratio), int(h * ratio)
        elif width is not None:
            ratio = width / w
            new_w, new_h = width, int(h * ratio)
        else:  # height is not None
            ratio = height / h
            new_w, new_h = int(w * ratio), height
    else:
        new_w = width if width is not None else w
        new_h = height if height is not None else h
    
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _crop_image(img: np.ndarray, x: int, y: int, width: int, height: int) -> np.ndarray:
    """Crop an image."""
    return img[y:y+height, x:x+width]


def _convert_to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert an image to grayscale."""
    if len(img.shape) == 3 and img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _apply_blur(img: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """Apply Gaussian blur to an image."""
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)


def _apply_threshold(img: np.ndarray, threshold: int = 127, 
                   max_val: int = 255, type: str = 'binary') -> np.ndarray:
    """Apply a threshold to an image."""
    if len(img.shape) == 3:
        img = _convert_to_grayscale(img)
    
    if type == 'binary':
        _, result = cv2.threshold(img, threshold, max_val, cv2.THRESH_BINARY)
    elif type == 'binary_inv':
        _, result = cv2.threshold(img, threshold, max_val, cv2.THRESH_BINARY_INV)
    elif type == 'trunc':
        _, result = cv2.threshold(img, threshold, max_val, cv2.THRESH_TRUNC)
    elif type == 'tozero':
        _, result = cv2.threshold(img, threshold, max_val, cv2.THRESH_TOZERO)
    elif type == 'tozero_inv':
        _, result = cv2.threshold(img, threshold, max_val, cv2.THRESH_TOZERO_INV)
    else:
        raise ValueError(f"Unknown threshold type: {type}")
    
    return result


def _rotate_image(img: np.ndarray, angle: float, center: Tuple[int, int] = None, 
                scale: float = 1.0) -> np.ndarray:
    """Rotate an image by the given angle."""
    h, w = img.shape[:2]
    
    if center is None:
        center = (w // 2, h // 2)
    
    M = cv2.getRotationMatrix2D(center, angle, scale)
    return cv2.warpAffine(img, M, (w, h))
