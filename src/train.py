"""CLI-тренировка U-Net / Attention U-Net / U-Net++ для сегментации ледников.

Использование:
    python -m src.train --year 2020 --epochs 100 --focal
    python -m src.train --year 2020 --no-attention
    python -m src.train --model unet_plus_plus --year 2020
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import config as default_config
from .models import build_data_generator, build_model, compile_model

sys.setrecursionlimit(10000)


@dataclass
class TrainConfig:
    year: int = 2020
    epochs: int = default_config.EPOCHS
    batch_size: int = default_config.BATCH_SIZE
    learning_rate: float = default_config.LEARNING_RATE
    use_focal: bool = False
    model_name: str = default_config.MODEL_NAME

    @property
    def model_prefix(self) -> str:
        return self.model_name

    def patches_dir(self) -> Path:
        return default_config.DATA_PATCHES / str(self.year)

    def models_dir(self) -> Path:
        return default_config.MODELS_DIR

    def results_dir(self) -> Path:
        return default_config.RESULTS_DIR


def setup_callbacks(train_cfg: TrainConfig):
    import tensorflow as tf

    callbacks = []

    callbacks.append(
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_dice_coefficient",
            mode="max",
            factor=default_config.LR_FACTOR,
            patience=default_config.LR_PATIENCE,
            min_lr=default_config.MIN_LR,
            verbose=1,
        )
    )

    callbacks.append(
        tf.keras.callbacks.EarlyStopping(
            monitor="val_dice_coefficient",
            mode="max",
            patience=default_config.EARLY_STOP_PATIENCE,
            restore_best_weights=True,
            verbose=1,
        )
    )

    callbacks.append(
        tf.keras.callbacks.ModelCheckpoint(
            str(train_cfg.models_dir() / f"{train_cfg.model_prefix}_best"),  # SavedModel dir
            monitor="val_dice_coefficient",
            mode="max",
            save_best_only=True,
            save_format="tf",  # TF SavedModel, не legacy HDF5
            verbose=1,
        )
    )

    callbacks.append(
        tf.keras.callbacks.CSVLogger(
            str(train_cfg.results_dir() / "training_log.csv"),
        )
    )

    return callbacks


def load_data(train_cfg: TrainConfig):
    patches_dir = train_cfg.patches_dir()
    X_train = np.load(patches_dir / "X_train.npy")
    y_train = np.load(patches_dir / "y_train.npy")
    X_val = np.load(patches_dir / "X_val.npy")
    y_val = np.load(patches_dir / "y_val.npy")
    X_test = np.load(patches_dir / "X_test.npy")
    y_test = np.load(patches_dir / "y_test.npy")
    return X_train, y_train, X_val, y_val, X_test, y_test


def train(train_cfg: TrainConfig):
    import tensorflow as tf

    tf.random.set_seed(default_config.RANDOM_SEED)
    np.random.seed(default_config.RANDOM_SEED)

    print(f"Загрузка данных за {train_cfg.year}...")
    X_train, y_train, X_val, y_val, X_test, y_test = load_data(train_cfg)
    print(f"Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")

    input_shape = (default_config.PATCH_SIZE, default_config.PATCH_SIZE, default_config.N_CHANNELS)
    print(f"Сборка модели ({train_cfg.model_name})...")
    model = build_model(input_shape)
    model = compile_model(model, learning_rate=train_cfg.learning_rate, use_focal=train_cfg.use_focal)

    model.summary()

    GlacierDataGenerator = build_data_generator()
    train_gen = GlacierDataGenerator(X_train, y_train, batch_size=train_cfg.batch_size, augment=True)
    val_gen = GlacierDataGenerator(X_val, y_val, batch_size=train_cfg.batch_size, augment=False)

    callbacks = setup_callbacks(train_cfg)

    print(f"Обучение ({train_cfg.epochs} эпох, batch={train_cfg.batch_size})...")
    history = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=train_cfg.epochs,
        callbacks=callbacks,
        verbose=1,
    )

    print("Оценка на тесте...")
    test_gen = GlacierDataGenerator(X_test, y_test, batch_size=train_cfg.batch_size, augment=False)
    metrics = model.evaluate(test_gen, verbose=1)
    metric_names = [m.name if hasattr(m, "name") else str(m) for m in model.metrics]
    for name, val in zip(metric_names, metrics):
        print(f"  {name}: {val:.4f}")

    # Save as TF SavedModel (replaces legacy HDF5 .h5)
    final_model_path = train_cfg.models_dir() / f"{train_cfg.model_prefix}_final_{train_cfg.year}"
    model.save(str(final_model_path), save_format="tf")
    print(f"Модель сохранена: {final_model_path}")

    return history, metrics


def main():
    parser = argparse.ArgumentParser(description="Обучение U-Net для сегментации ледников")
    parser.add_argument("--year", type=int, default=2020, help="Год данных")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--focal", action="store_true", help="Использовать Focal Loss")
    parser.add_argument(
        "--model",
        choices=["unet", "attention_unet", "unet_plus_plus"],
        default=default_config.MODEL_NAME,
        help="Архитектура модели (default: config.MODEL_NAME)",
    )
    args = parser.parse_args()

    train_cfg = TrainConfig(
        year=args.year,
        epochs=args.epochs or default_config.EPOCHS,
        batch_size=args.batch_size or default_config.BATCH_SIZE,
        learning_rate=args.lr or default_config.LEARNING_RATE,
        use_focal=args.focal,
        model_name=args.model,
    )

    train(train_cfg)


if __name__ == "__main__":
    main()
