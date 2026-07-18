"""
Script training model LSTM Global.

Entry point untuk menjalankan pipeline training secara manual atau terjadwal.

Cara penggunaan:
    python scripts/train.py
"""

import os
import sys

# Tambah root project ke sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logger import setup_logging
from app.ml.training.trainer import run_training

if __name__ == "__main__":
    setup_logging()
    run_training()
