"""
Tests for src.vision_transformer
"""

import pytest

pytestmark = pytest.mark.experimental



class TestViTConfig:
    """Tests for ViTConfig."""

    def test_import(self):
        from src.vision_transformer import ViTConfig
        assert ViTConfig is not None

    def test_initialization(self):
        from src.vision_transformer import ViTConfig
        config = ViTConfig(image_size=64, patch_size=16, num_channels=11, embed_dim=64)
        assert config.image_size == 64
        assert config.patch_size == 16

    def test_defaults(self):
        from src.vision_transformer import ViTConfig
        config = ViTConfig()
        assert config.image_size == 256
        assert config.embed_dim == 768
        assert config.num_heads == 12


class TestPatchEmbeddingLayer:
    """Tests for PatchEmbeddingLayer."""

    def test_import(self):
        from src.vision_transformer import PatchEmbeddingLayer
        assert PatchEmbeddingLayer is not None

    def test_initialization(self):
        from src.vision_transformer import PatchEmbeddingLayer, ViTConfig
        config = ViTConfig(image_size=64, patch_size=16, num_channels=11, embed_dim=64)
        layer = PatchEmbeddingLayer(config)
        assert layer is not None

    def test_num_patches(self):
        from src.vision_transformer import PatchEmbeddingLayer, ViTConfig
        config = ViTConfig(image_size=64, patch_size=16, num_channels=11, embed_dim=64)
        PatchEmbeddingLayer(config)
        expected = (64 // 16) ** 2
        assert config.num_patches == expected


class TestMultiHeadAttentionLayer:
    """Tests for MultiHeadAttentionLayer."""

    def test_import(self):
        from src.vision_transformer import MultiHeadAttentionLayer
        assert MultiHeadAttentionLayer is not None

    def test_initialization(self):
        from src.vision_transformer import MultiHeadAttentionLayer, ViTConfig
        config = ViTConfig(image_size=64, patch_size=16, embed_dim=64, num_heads=4)
        mha = MultiHeadAttentionLayer(config)
        assert mha is not None


class TestTransformerEncoderBlock:
    """Tests for TransformerEncoderBlock."""

    def test_import(self):
        from src.vision_transformer import TransformerEncoderBlock
        assert TransformerEncoderBlock is not None

    def test_initialization(self):
        from src.vision_transformer import TransformerEncoderBlock, ViTConfig
        config = ViTConfig(image_size=64, patch_size=16, embed_dim=64, num_heads=4, mlp_dim=128)
        block = TransformerEncoderBlock(config)
        assert block is not None


class TestBuildVitForGlacier:
    """Tests for build_vit_for_glacier."""

    def test_import(self):
        from src.vision_transformer import build_vit_for_glacier
        assert build_vit_for_glacier is not None

    def test_build_small(self):
        from src.vision_transformer import build_vit_for_glacier
        model = build_vit_for_glacier(
            image_size=64, patch_size=16, num_channels=11,
            num_classes=2, embed_dim=64, num_heads=4,
            num_layers=2, mlp_dim=128,
        )
        assert model is not None
        assert model.output_shape[-1] == 2

    def test_forward_pass(self):
        import tensorflow as tf

        from src.vision_transformer import build_vit_for_glacier
        model = build_vit_for_glacier(
            image_size=64, patch_size=16, num_channels=11,
            num_classes=2, embed_dim=64, num_heads=4,
            num_layers=2, mlp_dim=128,
        )
        x = tf.random.normal((2, 64, 64, 11))
        output = model(x, training=False)
        assert output.shape == (2, 2)

    def test_train_step(self):
        import tensorflow as tf

        from src.vision_transformer import build_vit_for_glacier
        model = build_vit_for_glacier(
            image_size=64, patch_size=16, num_channels=11,
            num_classes=2, embed_dim=32, num_heads=2,
            num_layers=1, mlp_dim=64,
        )
        optimizer = tf.keras.optimizers.Adam(1e-3)
        loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
        x = tf.random.normal((2, 64, 64, 11))
        y = tf.constant([0, 1])
        with tf.GradientTape() as tape:
            logits = model(x, training=True)
            loss = loss_fn(y, logits)
        grads = tape.gradient(loss, model.trainable_variables)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))
        assert loss.numpy() >= 0
