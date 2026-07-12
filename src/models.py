"""
U-Net архитектура, функции потерь, метрики и генератор данных для
семантической сегментации ледников.
"""

from __future__ import annotations

import numpy as np

from . import config

# ----------------------------------------------------------------------
# ГЕНЕРАТОР ДАННЫХ С АУГМЕНТАЦИЕЙ
# ----------------------------------------------------------------------


def build_data_generator():
    """Возвращает класс GlacierDataGenerator(tf.keras.utils.Sequence).

    Обёрнуто в функцию, чтобы импорт tensorflow происходил лениво —
    модуль models.py можно импортировать (например, для констант)
    даже без установленного TensorFlow.
    """
    import tensorflow as tf

    from .augmentation import augment_patch

    class GlacierDataGenerator(tf.keras.utils.Sequence):
        def __init__(
            self, X, y, batch_size=config.BATCH_SIZE, augment=False, shuffle=True, seed=config.RANDOM_SEED, **kwargs
        ):
            super().__init__(**kwargs)
            self.X = X
            self.y = y
            self.batch_size = batch_size
            self.augment = augment
            self.shuffle = shuffle
            self.rng = np.random.default_rng(seed)
            self.indices = np.arange(len(X))
            if shuffle:
                self.rng.shuffle(self.indices)

        def __len__(self):
            return max(1, int(np.ceil(len(self.X) / self.batch_size)))

        def __getitem__(self, idx):
            batch_idx = self.indices[idx * self.batch_size : (idx + 1) * self.batch_size]
            X_batch = self.X[batch_idx].astype(np.float32)
            y_batch = self.y[batch_idx].astype(np.float32)[..., np.newaxis]

            if self.augment:
                photometric_channels = min(len(config.S2_BANDS), X_batch.shape[-1])
                for i in range(len(X_batch)):
                    img, msk = augment_patch(
                        X_batch[i],
                        y_batch[i, ..., 0],
                        self.rng,
                        photometric_channels=photometric_channels,
                    )
                    X_batch[i] = img
                    y_batch[i, ..., 0] = msk

            return X_batch, y_batch

        def on_epoch_end(self):
            if self.shuffle:
                self.rng.shuffle(self.indices)

    return GlacierDataGenerator


# ----------------------------------------------------------------------
# АРХИТЕКТУРА U-NET
# ----------------------------------------------------------------------


def conv_block(x, filters, kernel_size=3):
    """Conv -> BN -> ReLU -> Conv -> BN -> ReLU."""
    from tensorflow.keras import layers

    x = layers.Conv2D(filters, kernel_size, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)
    x = layers.Conv2D(filters, kernel_size, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)
    return x


# ----------------------------------------------------------------------
# ATTENTION GATE
# ----------------------------------------------------------------------


def attention_gate(x, g, inter_channels=None):
    """Attention Gate для фокусировки на релевантных регионах.

    x : tensor — skip connection от энкодера
    g : tensor — gating signal от декодера (upsampled)
    """
    from tensorflow.keras import layers

    if inter_channels is None:
        inter_channels = max(x.shape[-1] // 2, 1)

    theta_x = layers.Conv2D(inter_channels, 1, padding="same", use_bias=False)(x)
    theta_x = layers.BatchNormalization()(theta_x)

    phi_g = layers.Conv2D(inter_channels, 1, padding="same", use_bias=False)(g)
    phi_g = layers.BatchNormalization()(phi_g)

    f = layers.Activation("relu")(theta_x + phi_g)
    psi = layers.Conv2D(1, 1, padding="same", use_bias=False)(f)
    psi = layers.BatchNormalization()(psi)
    psi = layers.Activation("sigmoid")(psi)

    return layers.Multiply()([x, psi])


# ----------------------------------------------------------------------
# U-Net (v1 — базовый)
# ----------------------------------------------------------------------


def build_unet(input_shape, filters=None, dropout_rate=0.1):
    """Строит базовый U-Net с BatchNorm и Dropout.

    Параметры
    ---------
    input_shape : tuple (H, W, C)
    filters : list[int]
        Количество фильтров на каждом уровне энкодера.
    """
    import tensorflow as tf
    from tensorflow.keras import Model, layers

    if filters is None:
        filters = config.UNET_FILTERS

    inputs = tf.keras.Input(input_shape)

    enc_outputs = []
    x = inputs
    for f in filters:
        x = conv_block(x, f)
        enc_outputs.append(x)
        x = layers.MaxPooling2D(2)(x)
        x = layers.Dropout(dropout_rate)(x)

    x = conv_block(x, filters[-1] * 2)

    for f, skip in zip(reversed(filters), reversed(enc_outputs)):
        x = layers.UpSampling2D(2)(x)
        x = layers.Concatenate()([x, skip])
        x = conv_block(x, f)

    outputs = layers.Conv2D(1, 1, activation="sigmoid")(x)

    return Model(inputs, outputs, name="U-Net")


# ----------------------------------------------------------------------
# Attention U-Net (v2)
# ----------------------------------------------------------------------


def build_attention_unet(input_shape, filters=None, dropout_rate=0.1):
    """Строит U-Net с Attention Gates на skip connections.

    Attention gates подавляют нерелевантные признаки из энкодера,
    фокусируясь на областях, релевантных сегментации (Oktay et al., 2018).
    """
    import tensorflow as tf
    from tensorflow.keras import Model, layers

    if filters is None:
        filters = config.UNET_FILTERS

    inputs = tf.keras.Input(input_shape)

    enc_outputs = []
    x = inputs
    for f in filters:
        x = conv_block(x, f)
        enc_outputs.append(x)
        x = layers.MaxPooling2D(2)(x)
        x = layers.Dropout(dropout_rate)(x)

    x = conv_block(x, filters[-1] * 2)

    for i, (f, skip) in enumerate(zip(reversed(filters), reversed(enc_outputs))):
        x = layers.UpSampling2D(2)(x)
        skip = attention_gate(skip, x)
        x = layers.Concatenate()([x, skip])
        x = conv_block(x, f)

    outputs = layers.Conv2D(1, 1, activation="sigmoid")(x)

    return Model(inputs, outputs, name="Attention-U-Net")


# ----------------------------------------------------------------------
# U-NET++ (NESTED U-NET)
# ----------------------------------------------------------------------


def _nested_conv_block(x, filters, dropout_rate=0.1):
    """Dense conv block with residual-style concat for U-Net++."""
    from tensorflow.keras import layers

    x1 = conv_block(x, filters)
    x1 = layers.Dropout(dropout_rate)(x1)
    return x1


def build_unet_plus_plus(input_shape, filters=None, dropout_rate=0.1):
    """U-Net++ с настоящими dense skip connections (Zhou et al. 2018).

    Реализует полную 4-уровневую версию с узлами X_{i,j} по нотации статьи:
        X_{i,j} = H( [X_{i,k} for k<j]  +  Up(X_{i+1, j-1}) )

    Колонки j=0..4 для уровней i=0..3:
    - j=0: энкодер (x00..x30 + боттлнек x40)
    - j=1: первый декодер — cross-соединения только от энкодерных узлов
    - j=2: добавляет узлы из j=1
    - j=3: добавляет узлы из j=2
    - j=4: финальный узел x04 — вход для выходного Conv1x1

    Главное отличие от базового U-Net: x_{i,j} получает ВСЕ предыдущие
    узлы X_{i,0..j-1} на том же пространственном уровне, а не только один.
    """
    import tensorflow as tf
    from tensorflow.keras import Model, layers

    if filters is None:
        filters = config.UNET_FILTERS

    f = list(filters)
    if len(f) < 5:
        f.append(f[-1] * 2)
    inputs = tf.keras.Input(input_shape)

    # ---- Column j=0: Encoder ----
    x00 = _nested_conv_block(inputs, f[0], dropout_rate)
    p0 = layers.MaxPooling2D(2)(x00)

    x10 = _nested_conv_block(p0, f[1], dropout_rate)
    p1 = layers.MaxPooling2D(2)(x10)

    x20 = _nested_conv_block(p1, f[2], dropout_rate)
    p2 = layers.MaxPooling2D(2)(x20)

    x30 = _nested_conv_block(p2, f[3], dropout_rate)
    p3 = layers.MaxPooling2D(2)(x30)

    x40 = _nested_conv_block(p3, f[4], dropout_rate)  # bottleneck

    # ---- Column j=1: X_{i,1} = H(X_{i,0}, Up(X_{i+1,0})) ----
    x31 = _nested_conv_block(layers.Concatenate()([x30, layers.UpSampling2D(2)(x40)]), f[3], dropout_rate)
    x21 = _nested_conv_block(layers.Concatenate()([x20, layers.UpSampling2D(2)(x30)]), f[2], dropout_rate)
    x11 = _nested_conv_block(layers.Concatenate()([x10, layers.UpSampling2D(2)(x20)]), f[1], dropout_rate)
    x01 = _nested_conv_block(layers.Concatenate()([x00, layers.UpSampling2D(2)(x10)]), f[0], dropout_rate)

    # ---- Column j=2: X_{i,2} = H(X_{i,0}, X_{i,1}, Up(X_{i+1,1})) ----
    x22 = _nested_conv_block(layers.Concatenate()([x20, x21, layers.UpSampling2D(2)(x31)]), f[2], dropout_rate)
    x12 = _nested_conv_block(layers.Concatenate()([x10, x11, layers.UpSampling2D(2)(x21)]), f[1], dropout_rate)
    x02 = _nested_conv_block(layers.Concatenate()([x00, x01, layers.UpSampling2D(2)(x11)]), f[0], dropout_rate)

    # ---- Column j=3: X_{i,3} = H(X_{i,0..2}, Up(X_{i+1,2})) ----
    x13 = _nested_conv_block(layers.Concatenate()([x10, x11, x12, layers.UpSampling2D(2)(x22)]), f[1], dropout_rate)
    x03 = _nested_conv_block(layers.Concatenate()([x00, x01, x02, layers.UpSampling2D(2)(x12)]), f[0], dropout_rate)

    # ---- Column j=4: X_{0,4} = H(X_{0,0..3}, Up(X_{1,3})) ----
    x04 = _nested_conv_block(
        layers.Concatenate()([x00, x01, x02, x03, layers.UpSampling2D(2)(x13)]),
        f[0],
        dropout_rate,
    )

    outputs = layers.Conv2D(1, 1, activation="sigmoid")(x04)
    return Model(inputs, outputs, name="unet_plus_plus")


# ----------------------------------------------------------------------
# MODEL REGISTRY
# ----------------------------------------------------------------------


MODEL_REGISTRY: dict[str, callable] = {
    "unet": build_unet,
    "attention_unet": build_attention_unet,
    "unet_plus_plus": build_unet_plus_plus,
}


def list_models() -> list[str]:
    """Возвращает список доступных архитектур."""
    return list(MODEL_REGISTRY.keys())


def build_model_by_name(name: str, input_shape=None, filters=None, dropout_rate=0.1):
    """Строит модель по имени из реестра.

    Raises
    ------
    ValueError
        Если имя модели не найдено в реестре.
    """
    if name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model '{name}'. Available: {list_models()}")
    builder = MODEL_REGISTRY[name]
    kwargs = {}
    if input_shape is not None:
        kwargs["input_shape"] = input_shape
    if filters is not None:
        kwargs["filters"] = filters
    if dropout_rate is not None:
        kwargs["dropout_rate"] = dropout_rate
    return builder(**kwargs)


def get_model_info(name: str) -> dict:
    """Возвращает метаданные модели из реестра."""
    if name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model '{name}'. Available: {list_models()}")
    return {
        "name": name,
        "builder": MODEL_REGISTRY[name].__name__,
        "doc": (MODEL_REGISTRY[name].__doc__ or "").strip().split("\n")[0],
    }


# ----------------------------------------------------------------------
# ВЫБОР МОДЕЛИ (LEGACY + REGISTRY)
# ----------------------------------------------------------------------


def build_model(input_shape=None, filters=None, dropout_rate=0.1):
    """Строит модель согласно config.MODEL_NAME (единственный управляющий параметр)."""
    if input_shape is None:
        input_shape = (config.PATCH_SIZE, config.PATCH_SIZE, config.N_CHANNELS)
    return build_model_by_name(config.MODEL_NAME, input_shape, filters, dropout_rate)


# ----------------------------------------------------------------------
# ФУНКЦИИ ПОТЕРЬ И МЕТРИКИ
# Re-exported from src.losses to avoid duplication.
# ----------------------------------------------------------------------

from .losses import combined_bce_dice_loss as combined_loss  # noqa: E402
from .losses import combined_focal_dice_loss as combined_focal_loss  # noqa: E402
from .losses import dice_coefficient, dice_loss, focal_loss  # noqa: E402


def get_custom_objects():
    """custom_objects для tf.keras.models.load_model(...).

    Merges local aliases with the full loss registry from src.losses.
    """
    from src import losses as loss_registry

    objs = {
        "combined_loss": combined_loss,
        "combined_focal_loss": combined_focal_loss,
        "focal_loss": focal_loss,
        "dice_coefficient": dice_coefficient,
        "dice_loss": dice_loss,
        "combined_bce_dice_loss": combined_loss,
        "combined_focal_dice_loss": combined_focal_loss,
    }
    for name, fn in loss_registry.get_custom_objects().items():
        objs.setdefault(name, fn)
    return objs


def compile_model(model, learning_rate=config.LEARNING_RATE, use_focal=False):
    import tensorflow as tf

    loss_fn = combined_focal_loss if use_focal else combined_loss

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=loss_fn,
        metrics=[
            dice_coefficient,
            tf.keras.metrics.BinaryIoU(target_class_ids=[1], threshold=0.5),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )
    return model


# ----------------------------------------------------------------------
# СКОЛЬЗЯЩЕЕ ОКНО ДЛЯ ИНФЕРЕНСА НА ПОЛНОМ СНИМКЕ
# ----------------------------------------------------------------------


def predict_full_image(image: np.ndarray, model, patch_size: int = config.PATCH_SIZE, threshold: float = 0.5):
    """Применяет модель к снимку произвольного размера через скользящее
    окно с 50% перекрытием, усредняя перекрывающиеся предсказания.

    Возвращает (probability_map, binary_mask), обе формы (H, W).
    """
    full_pred, count_map = _sliding_window_predict(image, model, patch_size)
    full_pred = full_pred / np.maximum(count_map, 1)
    binary_mask = (full_pred > threshold).astype(np.uint8)
    return full_pred, binary_mask


def mc_dropout_predict(image: np.ndarray, model, n_runs: int = 20, patch_size: int = config.PATCH_SIZE):
    """Monte-Carlo Dropout: n_runs прогонов с активным Dropout для оценки
    неопределённости предсказания (Идея D из исследовательской базы).

    Возвращает (mean_prob, std_prob) формы (H, W).
    """
    import tensorflow as tf

    @tf.function
    def predict_with_dropout(x):
        return model(x, training=True)

    H, W, C = image.shape
    runs = np.zeros((n_runs, H, W), dtype=np.float32)

    for r in range(n_runs):
        full_pred, count_map = _sliding_window_predict(
            image, model, patch_size, predict_fn=lambda p: predict_with_dropout(p)[0, ..., 0].numpy()
        )
        runs[r] = full_pred / np.maximum(count_map, 1)

    return runs.mean(axis=0), runs.std(axis=0)


def _sliding_window_predict(image, model, patch_size, predict_fn=None):
    """Общая логика скользящего окна для predict_full_image и mc_dropout_predict.

    Возвращает (full_pred, count_map) формы (H, W).
    """
    H, W, C = image.shape
    full_pred = np.zeros((H, W), dtype=np.float32)
    count_map = np.zeros((H, W), dtype=np.float32)

    if predict_fn is None:

        def predict_fn(p):
            return model.predict(p, verbose=0)[0, ..., 0]

    stride = patch_size // 2
    for i in range(0, H, stride):
        for j in range(0, W, stride):
            i_end = min(i + patch_size, H)
            j_end = min(j + patch_size, W)
            i_start = max(i_end - patch_size, 0)
            j_start = max(j_end - patch_size, 0)

            patch = image[i_start:i_end, j_start:j_end, :]

            if patch.shape[0] < patch_size or patch.shape[1] < patch_size:
                padded = np.zeros((patch_size, patch_size, C), dtype=np.float32)
                padded[: patch.shape[0], : patch.shape[1], :] = patch
                patch = padded

            pred = predict_fn(patch[np.newaxis, ...].astype(np.float32))

            full_pred[i_start:i_end, j_start:j_end] += pred[: i_end - i_start, : j_end - j_start]
            count_map[i_start:i_end, j_start:j_end] += 1

    return full_pred, count_map


# ----------------------------------------------------------------------
# TTA (TEST TIME AUGMENTATION)
# ----------------------------------------------------------------------


def tta_predict(model, image: np.ndarray, threshold: float = 0.5):
    """Test-Time Augmentation: усредняет предсказания по всем
    комбинациям flip/rot для более стабильного результата.

    Возвращает (probability_map, binary_mask).
    """
    batch = image[np.newaxis, ...]
    preds = []

    # Оригинал
    preds.append(model.predict(batch, verbose=0)[0, ..., 0])

    if config.TTA_FLIP_LR:
        flipped = np.fliplr(image)
        batch_f = flipped[np.newaxis, ...]
        pred = np.fliplr(model.predict(batch_f, verbose=0)[0, ..., 0])
        preds.append(pred)

    if config.TTA_FLIP_UD:
        flipped = np.flipud(image)
        batch_f = flipped[np.newaxis, ...]
        pred = np.flipud(model.predict(batch_f, verbose=0)[0, ..., 0])
        preds.append(pred)

    if config.TTA_FLIP_LR and config.TTA_FLIP_UD:
        flipped = np.flipud(np.fliplr(image))
        batch_f = flipped[np.newaxis, ...]
        pred = np.flipud(np.fliplr(model.predict(batch_f, verbose=0)[0, ..., 0]))
        preds.append(pred)

    prob = np.mean(preds, axis=0)
    binary = (prob > threshold).astype(np.uint8)
    return prob, binary


def tta_predict_batch(model, X: np.ndarray, threshold: float = 0.5, batch_size: int = 16):
    """TTA для батча патчей. Возвращает (probabilities, binaries)."""
    preds = []
    raw = model.predict(X, batch_size=batch_size, verbose=0)[..., 0]
    preds.append(raw)

    if config.TTA_FLIP_LR:
        X_flr = np.flip(X, axis=2)
        pred_lr = np.flip(model.predict(X_flr, batch_size=batch_size, verbose=0)[..., 0], axis=2)
        preds.append(pred_lr)

    if config.TTA_FLIP_UD:
        X_fud = np.flip(X, axis=1)
        pred_ud = np.flip(model.predict(X_fud, batch_size=batch_size, verbose=0)[..., 0], axis=1)
        preds.append(pred_ud)

    if config.TTA_FLIP_LR and config.TTA_FLIP_UD:
        X_fb = np.flip(np.flip(X, axis=2), axis=1)
        pred_fb = np.flip(np.flip(model.predict(X_fb, batch_size=batch_size, verbose=0)[..., 0], axis=2), axis=1)
        preds.append(pred_fb)

    prob = np.mean(preds, axis=0)
    return prob, (prob > threshold).astype(np.uint8)


# ----------------------------------------------------------------------
# CRF (CONDITIONAL RANDOM FIELD) — СГЛАЖИВАНИЕ
# ----------------------------------------------------------------------


def apply_crf(prob_map: np.ndarray, rgb: np.ndarray | None = None) -> np.ndarray:
    """CRF-сглаживание вероятностной карты с учётом RGB-пикселей.

    Убирает «соль-перец» и уточняет границы. Если pydensecrf не
    установлен — возвращает исходную маску.
    """
    try:
        import pydensecrf.densecrf as dcrf
    except ImportError:
        return prob_map

    H, W = prob_map.shape
    n_labels = 2

    unary = np.zeros((n_labels, H, W), dtype=np.float32)
    unary[1] = prob_map
    unary[0] = 1 - prob_map
    unary = -np.log(np.clip(unary, 1e-8, 1 - 1e-8))

    d = dcrf.DenseCRF2D(W, H, n_labels)
    d.setUnaryEnergy(unary)
    d.addPairwiseGaussian(sxy=config.CRF_POS_XY_STD, compat=3)

    if rgb is not None:
        img = (rgb * 255).astype(np.uint8) if rgb.max() <= 1 else rgb.astype(np.uint8)
        d.addPairwiseBilateral(sxy=config.CRF_BI_XY_STD, srgb=config.CRF_BI_RGB_STD, rgbim=img, compat=10)

    Q = d.inference(config.CRF_ITERATIONS)
    res = np.array(Q[1]).reshape(H, W)
    return res
