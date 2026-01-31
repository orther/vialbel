"""CLI argument parsing for headless Blender scripts.

Usage:
    blender -b -P script.py -- --out ./output --frames 1 120 --fps 24
"""
import sys
import argparse
from pathlib import Path


def parse_args():
    """Parse CLI arguments after Blender's '--' separator."""
    # Find args after '--'
    try:
        idx = sys.argv.index('--')
        args = sys.argv[idx + 1:]
    except ValueError:
        args = []

    parser = argparse.ArgumentParser(description="Blender label applicator animation")
    parser.add_argument('--out', type=str, default='./output',
                        help='Output directory for rendered frames')
    parser.add_argument('--frames', type=int, nargs=2, default=[1, 120],
                        metavar=('START', 'END'),
                        help='Frame range (start end)')
    parser.add_argument('--fps', type=int, default=24, help='Frames per second')
    parser.add_argument('--resolution', type=int, nargs=2, default=[1920, 1080],
                        metavar=('W', 'H'), help='Render resolution')
    parser.add_argument('--samples', type=int, default=64,
                        help='Render samples (Cycles)')
    parser.add_argument('--engine', type=str, default='CYCLES',
                        choices=['CYCLES', 'BLENDER_EEVEE'],
                        help='Render engine')
    parser.add_argument('--encode-mp4', action='store_true',
                        help='Encode frames to MP4 via ffmpeg after render')

    return parser.parse_args(args)
