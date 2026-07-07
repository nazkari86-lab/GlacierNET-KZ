"""
Сквозной тест U-Net на синтетических данных: построение модели,
генератор данных, 2 эпохи обучения, инференс через скользящее окно,
MC-Dropout.

Запуск: python3 _unet_smoke_test.py
(требует tensorflow; на CPU занимает ~1 минуту с маленькой моделью)
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np
from _synthetic_smoke_test import make_synthetic_scene

from src import config, metrics, models, preprocessing


def main():
    print("== Сборка синтетического датасета ==")
    pairs = [make_synthetic_scene(seed=s) for s in range(3)]
    X, y = preprocessing.build_dataset(pairs)
    X_train, X_val, X_test, y_train, y_val, y_test = preprocessing.train_val_test_split(X, y)
    print(f"train={len(X_train)} val={len(X_val)} test={len(X_test)}")

    print("\n== Построение маленькой U-Net (для скорости) ==")
    small_filters = [8, 16]
    unet = models.build_unet(
        input_shape=(config.PATCH_SIZE, config.PATCH_SIZE, config.N_CHANNELS),
        filters=small_filters,
    )
    unet = models.compile_model(unet)
    print("Параметров:", unet.count_params())

    print("\n== Генератор данных ==")
    GlacierDataGenerator = models.build_data_generator()
    train_gen = GlacierDataGenerator(X_train, y_train, batch_size=2, augment=True)
    val_gen = GlacierDataGenerator(X_val, y_val, batch_size=2, augment=False)
    print("len(train_gen) =", len(train_gen))

    print("\n== Обучение (2 эпохи, проверка что loss конечный) ==")
    history = unet.fit(train_gen, validation_data=val_gen, epochs=2, verbose=2)
    assert np.isfinite(history.history["loss"][-1])
    assert np.isfinite(history.history["val_loss"][-1])

    print("\n== Инференс через скользящее окно ==")
    image, mask_true = make_synthetic_scene(seed=42, h=300, w=300)
    prob_map, binary_mask = models.predict_full_image(image, unet, patch_size=config.PATCH_SIZE)
    assert prob_map.shape == (300, 300)
    assert binary_mask.shape == (300, 300)
    m = metrics.evaluate_segmentation(mask_true, binary_mask)
    print("Метрики на необученной/мало обученной модели (ожидаемо слабые):", m)

    print("\n== MC-Dropout (3 прогона, маленький снимок) ==")
    mean_prob, std_prob = models.mc_dropout_predict(image[:256, :256, :], unet, n_runs=3)
    assert mean_prob.shape == (256, 256)
    assert std_prob.shape == (256, 256)
    print("mean_prob range:", mean_prob.min(), mean_prob.max())
    print("std_prob range:", std_prob.min(), std_prob.max())

    print("\nВСЕ ТЕСТЫ U-NET ПРОЙДЕНЫ ✓")


if __name__ == "__main__":
    main()
