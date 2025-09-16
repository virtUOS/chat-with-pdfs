"""
Annotation system for PDF highlighting and source citation display.
"""

from .factory import create_annotations_from_sources
from .geometry import validate_and_clamp_coordinates, merge_nearby_positions, create_bounding_box

__all__ = [
    'create_annotations_from_sources',
    'validate_and_clamp_coordinates',
    'merge_nearby_positions',
    'create_bounding_box'
]