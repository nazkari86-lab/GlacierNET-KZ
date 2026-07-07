#!/usr/bin/env python3
"""Обучение U-Net++ для сегментации ледников.

Сохраняет лучшие веса в ``models/unet_plus_plus_best.h5`` (gitignored).

Предварительные условия:
  - Патчи за выбранный год: ``data/processed/patches/{year}/X_*.npy``
  - TensorFlow + GPU/CPU (обучение ~1–3 ч на Mac M-series, до 100 эпох с early stopping)

Примеры:
    python scripts/train_unet_plus_plus.py
    python scripts/train_unet_plus_plus.py --year 2020 --epochs 50
    python -m src.train --model unet_plus_plus --year 2020
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.train import TrainConfig, train


def main() -> None:
    parser = argparse.ArgumentParser(description="Обучение U-Net++ (GlacierNET-KZ)")
    parser.add_argument("--year", type=int, default=2020, help="Год патчей (папка data/processed/patches/{year})")
    parser.add_argument("--epochs", type=int, default=None, help=f"Макс. эпох (по умолчанию {config.EPOCHS})")
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--focal", action="store_true", help="Focal Loss вместо BCE+Dice")
    args = parser.parse_args()

    patches_dir = config.DATA_PATCHES / str(args.year)
    required = ["X_train.npy", "y_train.npy", "X_val.npy", "y_val.npy", "X_test.npy", "y_test.npy"]
    missing = [name for name in required if not (patches_dir / name).exists()]
    if missing:
        print(f"Ошибка: нет патчей в {patches_dir}")
        print("  Отсутствуют:", ", ".join(missing))
        print("  Сначала выполните notebooks/02_preprocessing.ipynb")
        sys.exit(1)

    out_path = config.MODELS_DIR / "unet_plus_plus_best.h5"
    print(f"Целевой файл весов: {out_path}")
    print(f"Патчи: {patches_dir} ({len(list(patches_dir.glob('*.npy')))} файлов)")

    train_cfg = TrainConfig(
        year=args.year,
        epochs=args.epochs or config.EPOCHS,
        batch_size=args.batch_size or config.BATCH_SIZE,
        learning_rate=args.lr or config.LEARNING_RATE,
        use_focal=args.focal,
        use_attention=False,
        model_name="unet_plus_plus",
    )
    train(train_cfg)
    print(f"Готово. Проверьте {out_path} и results/training_log.csv")


if __name__ == "__main__":
    main()
