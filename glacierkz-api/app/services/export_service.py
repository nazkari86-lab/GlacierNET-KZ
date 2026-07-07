"""
Сервис экспорта данных.

Предоставляет функции для экспорта:
- Масок сегментации в различных форматах
- Результатов предсказаний
- Моделей TensorFlow
- Геопространственных данных (GeoJSON)
"""

import json
import logging
import os
import struct
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class ExportService:
    """Сервис экспорта данных."""

    def __init__(self, exports_dir: str = "exports"):
        self.exports_dir = exports_dir
        os.makedirs(exports_dir, exist_ok=True)
        self._exports: Dict[str, Dict[str, Any]] = {}

    def export_masks_numpy(
        self,
        masks: np.ndarray,
        project_id: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Экспорт масок в формате NumPy (.npy)."""
        export_id = f"masks_{uuid.uuid4().hex[:12]}"
        if filename is None:
            filename = f"{export_id}.npy"

        filepath = os.path.join(self.exports_dir, filename)
        np.save(filepath, masks)

        file_size = os.path.getsize(filepath)
        metadata = {
            "export_id": export_id,
            "format": "numpy",
            "shape": list(masks.shape),
            "dtype": str(masks.dtype),
            "file_path": filepath,
            "file_size": file_size,
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._exports[export_id] = metadata
        logger.info(f"Маски экспортированы: {filepath} ({file_size} байт)")
        return metadata

    def export_masks_png(
        self,
        masks: np.ndarray,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Экспорт масок в PNG (каждый класс — отдельный файл)."""
        export_id = f"masks_{uuid.uuid4().hex[:12]}"
        export_dir = os.path.join(self.exports_dir, export_id)
        os.makedirs(export_dir, exist_ok=True)

        if masks.ndim == 2:
            masks = masks[np.newaxis, ...]

        file_paths = []
        total_size = 0
        for i in range(masks.shape[0]):
            filename = f"mask_{i:04d}.png"
            filepath = os.path.join(export_dir, filename)

            mask_uint8 = (masks[i] * 255).astype(np.uint8) if masks[i].max() <= 1.0 else masks[i].astype(np.uint8)
            self._write_png(filepath, mask_uint8)
            file_paths.append(filepath)
            total_size += os.path.getsize(filepath)

        metadata = {
            "export_id": export_id,
            "format": "png",
            "num_masks": masks.shape[0],
            "shape": list(masks.shape[1:]),
            "file_paths": file_paths,
            "total_size": total_size,
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._exports[export_id] = metadata
        logger.info(f"Маски PNG экспортированы: {len(file_paths)} файлов")
        return metadata

    def export_predictions_json(
        self,
        predictions: Dict[str, Any],
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Экспорт предсказаний в JSON."""
        export_id = f"pred_{uuid.uuid4().hex[:12]}"
        filepath = os.path.join(self.exports_dir, f"{export_id}.json")

        export_data = {
            "export_id": export_id,
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "predictions": predictions,
        }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        file_size = os.path.getsize(filepath)
        metadata = {
            "export_id": export_id,
            "format": "json",
            "file_path": filepath,
            "file_size": file_size,
            "project_id": project_id,
            "created_at": export_data["created_at"],
        }

        self._exports[export_id] = metadata
        logger.info(f"Предсказания экспортированы: {filepath}")
        return metadata

    def export_predictions_csv(
        self,
        predictions: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Экспорт предсказаний в CSV."""
        export_id = f"pred_{uuid.uuid4().hex[:12]}"
        filepath = os.path.join(self.exports_dir, f"{export_id}.csv")

        if not predictions:
            raise ValueError("Нет предсказаний для экспорта")

        if columns is None:
            columns = list(predictions[0].keys())

        with open(filepath, "w") as f:
            f.write(",".join(columns) + "\n")
            for pred in predictions:
                values = [str(pred.get(col, "")) for col in columns]
                f.write(",".join(values) + "\n")

        file_size = os.path.getsize(filepath)
        metadata = {
            "export_id": export_id,
            "format": "csv",
            "file_path": filepath,
            "file_size": file_size,
            "num_rows": len(predictions),
            "columns": columns,
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._exports[export_id] = metadata
        logger.info(f"Предсказания CSV экспортированы: {len(predictions)} строк")
        return metadata

    def export_model_h5(
        self,
        model: Any,
        model_name: str = "glacier_model",
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Экспорт модели в формате H5."""
        export_id = f"model_{uuid.uuid4().hex[:12]}"
        filepath = os.path.join(self.exports_dir, f"{export_id}_{model_name}.h5")

        model.save(filepath)
        file_size = os.path.getsize(filepath)

        metadata = {
            "export_id": export_id,
            "format": "h5",
            "model_name": model_name,
            "file_path": filepath,
            "file_size": file_size,
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._exports[export_id] = metadata
        logger.info(f"Модель экспортирована: {filepath} ({file_size} байт)")
        return metadata

    def export_geojson(
        self,
        features: List[Dict[str, Any]],
        project_id: Optional[str] = None,
        simplify_tolerance: float = 0.001,
    ) -> Dict[str, Any]:
        """Экспорт данных в GeoJSON."""
        export_id = f"geojson_{uuid.uuid4().hex[:12]}"
        filepath = os.path.join(self.exports_dir, f"{export_id}.geojson")

        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "export_id": export_id,
                "project_id": project_id,
                "simplify_tolerance": simplify_tolerance,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "num_features": len(features),
            },
        }

        with open(filepath, "w") as f:
            json.dump(geojson, f, indent=2)

        file_size = os.path.getsize(filepath)
        metadata = {
            "export_id": export_id,
            "format": "geojson",
            "file_path": filepath,
            "file_size": file_size,
            "num_features": len(features),
            "project_id": project_id,
            "created_at": geojson["metadata"]["created_at"],
        }

        self._exports[export_id] = metadata
        logger.info(f"GeoJSON экспортирован: {filepath} ({len(features)} объектов)")
        return metadata

    def get_export(self, export_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации об экспорте."""
        return self._exports.get(export_id)

    def list_exports(
        self,
        export_type: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Список всех экспортов."""
        exports = list(self._exports.values())

        if export_type:
            exports = [e for e in exports if e.get("export_type") == export_type]
        if project_id:
            exports = [e for e in exports if e.get("project_id") == project_id]

        exports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return exports

    def delete_export(self, export_id: str) -> bool:
        """Удаление экспорта."""
        if export_id not in self._exports:
            return False

        export = self._exports[export_id]
        file_path = export.get("file_path")

        if file_path and os.path.exists(file_path):
            if os.path.isdir(file_path):
                import shutil

                shutil.rmtree(file_path)
            else:
                os.remove(file_path)

        del self._exports[export_id]
        logger.info(f"Экспорт {export_id} удалён")
        return True

    def get_export_stats(self) -> Dict[str, Any]:
        """Статистика экспорта."""
        total = len(self._exports)
        total_size = sum(e.get("file_size", 0) for e in self._exports.values())

        by_format = {}
        for e in self._exports.values():
            fmt = e.get("format", "unknown")
            by_format[fmt] = by_format.get(fmt, 0) + 1

        return {
            "total_exports": total,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "by_format": by_format,
        }

    @staticmethod
    def _write_png(filepath: str, data: np.ndarray) -> None:
        """Запись массива в PNG без зависимостей от Pillow."""
        if data.ndim == 2:
            height, width = data.shape
            channels = 1
            raw = data.tobytes()
        elif data.ndim == 3 and data.shape[2] in (1, 3, 4):
            height, width, channels = data.shape
            raw = data.tobytes()
        else:
            raise ValueError(f"Неподдерживаемая форма массива: {data.shape}")

        def _make_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
            chunk = chunk_type + chunk_data
            crc = struct.pack(">I", _png_crc32(chunk))
            return struct.pack(">I", len(chunk_data)) + chunk + crc

        import zlib

        signature = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 0 if channels == 1 else 2, 0, 0, 0)
        ihdr = _make_chunk(b"IHDR", ihdr_data)

        compressed = zlib.compress(raw)
        idat = _make_chunk(b"IDAT", compressed)
        iend = _make_chunk(b"IEND", b"")

        with open(filepath, "wb") as f:
            f.write(signature + ihdr + idat + iend)


def _png_crc32(data: bytes) -> int:
    """CRC32 для PNG чанков."""
    import binascii

    return binascii.crc32(data) & 0xFFFFFFFF


export_service = ExportService()
