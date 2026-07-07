"""
Tests for src.multi_task_learning
"""

import pytest

pytestmark = pytest.mark.experimental



class TestMultiTaskConfig:
    """Tests for MultiTaskConfig."""

    def test_import(self):
        from src.multi_task_learning import MultiTaskConfig
        assert MultiTaskConfig is not None

    def test_initialization(self):
        from src.multi_task_learning import MultiTaskConfig
        config = MultiTaskConfig(image_size=128, num_channels=11, num_classes=3)
        assert config.image_size == 128
        assert config.num_channels == 11
        assert config.num_classes == 3

    def test_defaults(self):
        from src.multi_task_learning import MultiTaskConfig
        config = MultiTaskConfig()
        assert config.image_size == 256
        assert config.seg_weight == 1.0
        assert config.cls_weight == 0.5
        assert config.reg_weight == 0.3

    def test_encoder_filters(self):
        from src.multi_task_learning import MultiTaskConfig
        config = MultiTaskConfig()
        assert config.encoder_filters == (64, 128, 256, 512)


class TestBuildMultiTaskModel:
    """Tests for build_multi_task_model."""

    def test_import(self):
        from src.multi_task_learning import build_multi_task_model
        assert build_multi_task_model is not None

    def test_build_model(self):
        from src.multi_task_learning import MultiTaskConfig, build_multi_task_model
        config = MultiTaskConfig(image_size=64, num_channels=11, num_classes=2)
        model = build_multi_task_model(config)
        assert model is not None
        assert len(model.outputs) >= 1

    def test_model_forward_pass(self):
        import tensorflow as tf

        from src.multi_task_learning import MultiTaskConfig, build_multi_task_model
        config = MultiTaskConfig(image_size=64, num_channels=11, num_classes=2)
        model = build_multi_task_model(config)
        x = tf.random.normal((2, 64, 64, 11))
        outputs = model(x, training=False)
        assert outputs is not None


class TestSharedEncoder:
    """Tests for shared_encoder function."""

    def test_import(self):
        from src.multi_task_learning import shared_encoder
        assert shared_encoder is not None

    def test_build_encoder(self):
        import tensorflow as tf

        from src.multi_task_learning import MultiTaskConfig, shared_encoder
        config = MultiTaskConfig(image_size=64, num_channels=11)
        inputs = tf.keras.Input(shape=(64, 64, 11))
        features = shared_encoder(inputs, config)
        assert features is not None
        assert features.shape[-1] > 0


class TestClassificationHead:
    """Tests for classification_head function."""

    def test_import(self):
        from src.multi_task_learning import classification_head
        assert classification_head is not None

    def test_build_head(self):
        import tensorflow as tf

        from src.multi_task_learning import classification_head
        inputs = tf.keras.Input(shape=(8,))
        output = classification_head(inputs, num_classes=2, dropout_rate=0.2)
        assert output.shape[-1] == 2


class TestRegressionHead:
    """Tests for regression_head function."""

    def test_import(self):
        from src.multi_task_learning import regression_head
        assert regression_head is not None

    def test_build_head(self):
        import tensorflow as tf

        from src.multi_task_learning import regression_head
        inputs = tf.keras.Input(shape=(8,))
        output = regression_head(inputs, num_outputs=1, dropout_rate=0.2)
        assert output.shape[-1] == 1


class TestSegmentationHead:
    """Tests for segmentation_head function."""

    def test_import(self):
        from src.multi_task_learning import segmentation_head
        assert segmentation_head is not None

    def test_build_head(self):
        import tensorflow as tf

        from src.multi_task_learning import segmentation_head
        inputs = tf.keras.Input(shape=(16, 16, 64))
        output = segmentation_head(inputs, num_classes=1, filters=32)
        assert output is not None


class TestMultiTaskLoss:
    """Tests for multi_task_loss."""

    def test_import(self):
        from src.multi_task_learning import multi_task_loss
        assert multi_task_loss is not None

    def test_loss_function(self):
        from src.multi_task_learning import MultiTaskConfig, multi_task_loss
        config = MultiTaskConfig()
        loss_fn = multi_task_loss(config)
        assert callable(loss_fn)

    def test_loss_computation(self):
        import tensorflow as tf

        from src.multi_task_learning import MultiTaskConfig, multi_task_loss
        config = MultiTaskConfig(seg_weight=1.0, cls_weight=0.5, reg_weight=0.3)
        loss_fn = multi_task_loss(config)
        y_true_seg = tf.random.uniform((2, 64, 64, 1))
        y_pred_seg = tf.random.uniform((2, 64, 64, 1))
        y_true_cls = tf.constant([0, 1])
        y_pred_cls = tf.random.uniform((2, 2))
        y_true_reg = tf.random.uniform((2, 1))
        y_pred_reg = tf.random.uniform((2, 1))
        loss = loss_fn(
            (y_true_seg, y_true_cls, y_true_reg),
            (y_pred_seg, y_pred_cls, y_pred_reg),
        )
        assert loss.numpy() >= 0
