"""CLI-тренировка U-Net / Attention U-Net / U-Net++ для сегментации ледников.

Использование:
    python -m src.train --year 2020 --epochs 100 --focal
    python -m src.train --year 2020 --no-attention
    python -m src.train --model unet_plus_plus --year 2020
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import config as default_config
from .models import build_data_generator, build_model_by_name, compile_model

sys.setrecursionlimit(10000)


@dataclass
class TrainConfig:
    year: int = 2020
    patches_path: Path | None = None
    epochs: int = default_config.EPOCHS
    batch_size: int = default_config.BATCH_SIZE
    learning_rate: float = default_config.LEARNING_RATE
    use_focal: bool = False
    model_name: str = default_config.MODEL_NAME
    seed: int = default_config.RANDOM_SEED
    deterministic: bool = True
    modality_dropout_probability: float = 0.0
    resume_on_interruption: bool = True

    @property
    def model_prefix(self) -> str:
        return self.model_name

    @property
    def dataset_label(self) -> str:
        if self.patches_path is not None:
            return self.patches_path.name
        return str(self.year)

    def patches_dir(self) -> Path:
        if self.patches_path is not None:
            return self.patches_path
        return default_config.DATA_PATCHES / str(self.year)

    def models_dir(self) -> Path:
        return default_config.MODELS_DIR

    def results_dir(self) -> Path:
        return default_config.RESULTS_DIR


def setup_callbacks(train_cfg: TrainConfig):
    import tensorflow as tf

    train_cfg.models_dir().mkdir(parents=True, exist_ok=True)
    train_cfg.results_dir().mkdir(parents=True, exist_ok=True)
    callbacks = [tf.keras.callbacks.TerminateOnNaN()]
    if train_cfg.resume_on_interruption:
        callbacks.append(
            tf.keras.callbacks.BackupAndRestore(
                backup_dir=str(
                    train_cfg.results_dir() / "training_backups" / f"{train_cfg.model_prefix}_{train_cfg.dataset_label}"
                ),
                delete_checkpoint=True,
            )
        )

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
            str(train_cfg.models_dir() / f"{train_cfg.model_prefix}_best_{train_cfg.dataset_label}"),  # SavedModel dir
            monitor="val_dice_coefficient",
            mode="max",
            save_best_only=True,
            save_format="tf",  # TF SavedModel, не legacy HDF5
            verbose=1,
        )
    )

    callbacks.append(
        tf.keras.callbacks.CSVLogger(
            str(train_cfg.results_dir() / f"training_log_{train_cfg.model_prefix}_{train_cfg.dataset_label}.csv"),
        )
    )

    return callbacks


def _feature_schema(train_cfg: TrainConfig) -> list[str]:
    path = train_cfg.patches_dir() / "manifest.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("feature_schema", [])
    return [str(value) for value in values] if isinstance(values, list) else []


def _modality_groups(feature_schema: list[str]) -> list[tuple[int, ...]]:
    """Return only ancillary groups; optical channels are never fully erased."""
    groups: list[tuple[int, ...]] = []
    for names in (
        ("elevation_m_normalized", "slope_degrees_normalized", "aspect_degrees_normalized"),
        ("VV_dB_normalized", "VH_dB_normalized"),
    ):
        if all(name in feature_schema for name in names):
            groups.append(tuple(feature_schema.index(name) for name in names))
    return groups


def _git_commit(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_training_run_manifest(
    train_cfg: TrainConfig,
    *,
    input_shape: tuple[int, ...],
    split_sizes: dict[str, int],
) -> Path:
    """Persist enough provenance to reproduce a training run without secrets."""
    dataset_manifest = train_cfg.patches_dir() / "manifest.json"
    payload = {
        "schema": "glaciernet-kz.training-run.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_commit(default_config.PROJECT_ROOT),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dataset": str(train_cfg.patches_dir().resolve().relative_to(default_config.PROJECT_ROOT)),
        "dataset_manifest_sha256": (
            hashlib.sha256(dataset_manifest.read_bytes()).hexdigest() if dataset_manifest.is_file() else None
        ),
        "model_name": train_cfg.model_name,
        "input_shape": list(input_shape),
        "feature_schema": _feature_schema(train_cfg),
        "splits": split_sizes,
        "hyperparameters": {
            "epochs": train_cfg.epochs,
            "batch_size": train_cfg.batch_size,
            "learning_rate": train_cfg.learning_rate,
            "use_focal": train_cfg.use_focal,
            "seed": train_cfg.seed,
            "deterministic": train_cfg.deterministic,
            "modality_dropout_probability": train_cfg.modality_dropout_probability,
            "resume_on_interruption": train_cfg.resume_on_interruption,
        },
        "test_policy": "test split is loaded but never used by fit or threshold selection",
    }
    output = train_cfg.results_dir() / f"training_run_{train_cfg.model_prefix}_{train_cfg.dataset_label}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def load_data(train_cfg: TrainConfig):
    patches_dir = train_cfg.patches_dir()
    manifest_path = patches_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        year_entries = manifest.get("years")
        if isinstance(year_entries, list) and year_entries:
            return load_manifest_data(manifest, patches_dir)

    X_train = np.load(patches_dir / "X_train.npy")
    y_train = np.load(patches_dir / "y_train.npy")
    X_val = np.load(patches_dir / "X_val.npy")
    y_val = np.load(patches_dir / "y_val.npy")
    X_test = np.load(patches_dir / "X_test.npy")
    y_test = np.load(patches_dir / "y_test.npy")
    return X_train, y_train, X_val, y_val, X_test, y_test


def load_sample_weights(train_cfg: TrainConfig):
    """Load optional pixel reliability maps without weakening legacy datasets."""
    patches_dir = train_cfg.patches_dir()
    paths = [patches_dir / f"w_{split}.npy" for split in ("train", "val", "test")]
    present = [path.is_file() for path in paths]
    if not any(present):
        return None
    if not all(present):
        missing = [str(path) for path, exists in zip(paths, present) if not exists]
        raise ValueError(f"Sample-weight dataset is incomplete: {missing}")
    return tuple(np.load(path, mmap_mode="r") for path in paths)


def load_manifest_data(manifest: dict, manifest_dir: Path):
    if manifest.get("split_strategy") == "year_holdout":
        return load_year_holdout_manifest_data(manifest, manifest_dir)

    arrays: dict[str, list[np.ndarray]] = {
        "X_train": [],
        "y_train": [],
        "X_val": [],
        "y_val": [],
        "X_test": [],
        "y_test": [],
    }
    for entry in manifest["years"]:
        out_dir = resolve_entry_output_dir(entry, manifest_dir)
        for split_name in arrays:
            arrays[split_name].append(np.load(out_dir / f"{split_name}.npy"))

    return tuple(
        np.concatenate(arrays[name], axis=0) for name in ("X_train", "y_train", "X_val", "y_val", "X_test", "y_test")
    )


def resolve_entry_output_dir(entry: dict, manifest_dir: Path) -> Path:
    out_dir_raw = entry.get("output_dir")
    if not out_dir_raw:
        raise ValueError(f"Manifest entry has no output_dir: {entry}")
    out_dir = Path(out_dir_raw)
    if not out_dir.is_absolute():
        out_dir = default_config.PROJECT_ROOT / out_dir
    if not out_dir.exists():
        # Allow relocatable manifests where output_dir is relative to manifest dir.
        out_dir = manifest_dir / str(entry.get("year"))
    if not out_dir.exists():
        raise FileNotFoundError(f"Patch directory does not exist: {out_dir}")
    return out_dir


class ShardedArray:
    """Read-only array facade that materializes only the requested patch batch."""

    def __init__(self, shards: list[np.ndarray]):
        if not shards:
            raise ValueError("ShardedArray requires at least one shard")
        tail_shape = shards[0].shape[1:]
        dtype = shards[0].dtype
        if any(shard.shape[1:] != tail_shape or shard.dtype != dtype for shard in shards):
            raise ValueError("All ShardedArray shards must share shape and dtype after axis 0")
        self._shards = shards
        self._offsets = np.cumsum([0] + [len(shard) for shard in shards])
        self.shape = (int(self._offsets[-1]), *tail_shape)
        self.dtype = dtype
        self.ndim = len(self.shape)

    def __len__(self) -> int:
        return self.shape[0]

    def __getitem__(self, key):
        if isinstance(key, tuple):
            raise TypeError("ShardedArray supports indexing on axis 0 only")
        indices = np.arange(len(self))[key]
        scalar = np.isscalar(indices)
        flat = np.asarray(indices, dtype=int).reshape(-1)
        if np.any(flat < 0) or np.any(flat >= len(self)):
            raise IndexError("ShardedArray index out of range")
        output = np.empty((len(flat), *self.shape[1:]), dtype=self.dtype)
        for shard, start, end in zip(self._shards, self._offsets[:-1], self._offsets[1:]):
            positions = (flat >= start) & (flat < end)
            if np.any(positions):
                output[positions] = shard[flat[positions] - start]
        return output[0] if scalar else output

    def mean(self) -> float:
        total = sum(float(np.asarray(shard).sum(dtype=np.float64)) for shard in self._shards)
        count = sum(int(shard.size) for shard in self._shards)
        return total / count


def load_year_holdout_manifest_data(manifest: dict, manifest_dir: Path):
    """Load every patch from a year into exactly one temporal split."""
    split_years = {
        "train": {int(year) for year in manifest.get("train_years", [])},
        "val": {int(year) for year in manifest.get("val_years", [])},
        "test": {int(year) for year in manifest.get("test_years", [])},
    }
    if not all(split_years.values()):
        raise ValueError("year_holdout manifest requires non-empty train_years, val_years, and test_years")
    if (
        split_years["train"] & split_years["val"]
        or split_years["train"] & split_years["test"]
        or split_years["val"] & split_years["test"]
    ):
        raise ValueError("year_holdout manifest assigns a year to more than one split")

    arrays: dict[str, list[np.ndarray]] = {
        "X_train": [],
        "y_train": [],
        "X_val": [],
        "y_val": [],
        "X_test": [],
        "y_test": [],
    }
    manifest_years = {int(entry["year"]) for entry in manifest["years"]}
    assigned_years = set().union(*split_years.values())
    if assigned_years != manifest_years:
        raise ValueError(
            "year_holdout manifest split years must exactly match manifest years: "
            f"assigned={sorted(assigned_years)}, manifest={sorted(manifest_years)}"
        )

    for entry in manifest["years"]:
        year = int(entry["year"])
        split = next(name for name, years in split_years.items() if year in years)
        out_dir = resolve_entry_output_dir(entry, manifest_dir)
        for source_split in ("train", "val", "test"):
            arrays[f"X_{split}"].append(np.load(out_dir / f"X_{source_split}.npy", mmap_mode="r"))
            arrays[f"y_{split}"].append(np.load(out_dir / f"y_{source_split}.npy", mmap_mode="r"))

    return tuple(ShardedArray(arrays[name]) for name in ("X_train", "y_train", "X_val", "y_val", "X_test", "y_test"))


def train(train_cfg: TrainConfig):
    import tensorflow as tf

    tf.keras.utils.set_random_seed(train_cfg.seed)
    np.random.seed(train_cfg.seed)
    if train_cfg.deterministic:
        try:
            tf.config.experimental.enable_op_determinism()
        except (AttributeError, RuntimeError):
            pass

    print(f"Загрузка данных из {train_cfg.patches_dir()}...")
    X_train, y_train, X_val, y_val, X_test, y_test = load_data(train_cfg)
    sample_weights = load_sample_weights(train_cfg)
    if sample_weights is not None:
        w_train, w_val, w_test = sample_weights
        for split, labels, weights in (
            ("train", y_train, w_train),
            ("validation", y_val, w_val),
            ("test", y_test, w_test),
        ):
            if weights.shape != labels.shape:
                raise ValueError(f"{split} sample weights {weights.shape} do not match labels {labels.shape}")
        print("Используются явные карты надёжности пикселей (review zones down-weighted).")
    else:
        w_train = w_val = w_test = None
    print(f"Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")

    input_shape = tuple(int(value) for value in X_train.shape[1:])
    if len(input_shape) != 3 or input_shape[:2] != (default_config.PATCH_SIZE, default_config.PATCH_SIZE):
        raise ValueError(f"Unexpected training feature shape: {X_train.shape}")
    print(f"Сборка модели ({train_cfg.model_name})...")
    model = build_model_by_name(train_cfg.model_name, input_shape)
    model = compile_model(model, learning_rate=train_cfg.learning_rate, use_focal=train_cfg.use_focal)

    model.summary()

    GlacierDataGenerator = build_data_generator()
    feature_schema = _feature_schema(train_cfg)
    modality_groups = _modality_groups(feature_schema)
    if train_cfg.modality_dropout_probability and not modality_groups:
        raise ValueError("modality dropout requested, but no terrain/SAR groups exist in feature_schema")
    train_gen = GlacierDataGenerator(
        X_train,
        y_train,
        batch_size=train_cfg.batch_size,
        augment=True,
        seed=train_cfg.seed,
        modality_groups=modality_groups,
        modality_dropout_probability=train_cfg.modality_dropout_probability,
        sample_weights=w_train,
    )
    val_gen = GlacierDataGenerator(
        X_val,
        y_val,
        batch_size=train_cfg.batch_size,
        augment=False,
        sample_weights=w_val,
    )
    run_manifest = write_training_run_manifest(
        train_cfg,
        input_shape=input_shape,
        split_sizes={"train": len(X_train), "validation": len(X_val), "test": len(X_test)},
    )
    print(f"Training provenance: {run_manifest}")

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
    test_gen = GlacierDataGenerator(
        X_test,
        y_test,
        batch_size=train_cfg.batch_size,
        augment=False,
        sample_weights=w_test,
    )
    metrics = model.evaluate(test_gen, verbose=1)
    metric_names = [m.name if hasattr(m, "name") else str(m) for m in model.metrics]
    for name, val in zip(metric_names, metrics):
        print(f"  {name}: {val:.4f}")

    # Save as TF SavedModel (replaces legacy HDF5 .h5)
    final_model_path = train_cfg.models_dir() / f"{train_cfg.model_prefix}_final_{train_cfg.dataset_label}"
    model.save(str(final_model_path), save_format="tf")
    print(f"Модель сохранена: {final_model_path}")

    return history, metrics


def main():
    parser = argparse.ArgumentParser(description="Обучение U-Net для сегментации ледников")
    parser.add_argument("--year", type=int, default=2020, help="Год данных")
    parser.add_argument(
        "--patches-dir",
        type=Path,
        default=None,
        help="Каталог patch dataset. Может указывать на multi-year manifest directory.",
    )
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--focal", action="store_true", help="Использовать Focal Loss")
    parser.add_argument("--seed", type=int, default=default_config.RANDOM_SEED)
    parser.add_argument(
        "--modality-dropout",
        type=float,
        default=0.0,
        help="Experimental probability of dropping each ancillary modality group during training.",
    )
    parser.add_argument("--non-deterministic", action="store_true")
    parser.add_argument("--no-resume", action="store_true", help="Disable interruption-resume checkpoints")
    parser.add_argument(
        "--model",
        choices=["unet", "attention_unet", "unet_plus_plus"],
        default=default_config.MODEL_NAME,
        help="Архитектура модели (default: config.MODEL_NAME)",
    )
    args = parser.parse_args()

    train_cfg = TrainConfig(
        year=args.year,
        patches_path=args.patches_dir,
        epochs=args.epochs or default_config.EPOCHS,
        batch_size=args.batch_size or default_config.BATCH_SIZE,
        learning_rate=args.lr or default_config.LEARNING_RATE,
        use_focal=args.focal,
        model_name=args.model,
        seed=args.seed,
        deterministic=not args.non_deterministic,
        modality_dropout_probability=args.modality_dropout,
        resume_on_interruption=not args.no_resume,
    )

    train(train_cfg)


if __name__ == "__main__":
    main()
