"""Tests for src/preprocessing.py."""

import numpy as np

from src.preprocessing import augment_patch, create_patches, train_val_test_split


class TestCreatePatches:
    def test_output_shapes(self, sample_image, sample_mask):
        patches_img, patches_mask = create_patches(
            sample_image,
            sample_mask,
            patch_size=64,
            stride=64,
            min_glacier_fraction=0.0,
            background_keep_prob=1.0,
        )
        assert patches_img.ndim == 4
        assert patches_mask.ndim == 3
        assert patches_img.shape[1:] == (64, 64, 11)
        assert patches_mask.shape[1:] == (64, 64)

    def test_no_patches_when_all_filtered(self, rng):
        img = np.zeros((64, 64, 3), dtype=np.float32)
        mask = np.zeros((64, 64), dtype=np.uint8)
        patches_img, patches_mask = create_patches(
            img,
            mask,
            patch_size=64,
            stride=64,
            min_glacier_fraction=0.5,
            background_keep_prob=0.0,
            rng=rng,
        )
        assert patches_img.shape[0] == 0

    def test_preserves_glacier_patches(self, rng):
        img = np.ones((64, 64, 3), dtype=np.float32)
        mask = np.ones((64, 64), dtype=np.uint8)  # 100% glacier
        patches_img, patches_mask = create_patches(
            img,
            mask,
            patch_size=64,
            stride=64,
            min_glacier_fraction=0.5,
            background_keep_prob=0.0,
            rng=rng,
        )
        assert patches_img.shape[0] >= 1

    def test_stride_effect(self, sample_image, sample_mask):
        p1, _ = create_patches(
            sample_image, sample_mask, patch_size=64, stride=64, min_glacier_fraction=0.0, background_keep_prob=1.0
        )
        p2, _ = create_patches(
            sample_image, sample_mask, patch_size=64, stride=32, min_glacier_fraction=0.0, background_keep_prob=1.0
        )
        assert p2.shape[0] >= p1.shape[0]


class TestAugmentPatch:
    def test_preserves_shape(self, rng):
        img = rng.random((64, 64, 3), dtype=np.float32)
        mask = rng.integers(0, 2, (64, 64)).astype(np.uint8)
        img_out, mask_out = augment_patch(img, mask, rng=rng)
        assert img_out.shape == img.shape
        assert mask_out.shape == mask.shape

    def test_deterministic_with_seed(self):
        img = np.ones((32, 32, 3), dtype=np.float32)
        mask = np.ones((32, 32), dtype=np.uint8)
        r1 = augment_patch(img.copy(), mask.copy(), rng=np.random.default_rng(42))
        r2 = augment_patch(img.copy(), mask.copy(), rng=np.random.default_rng(42))
        np.testing.assert_array_equal(r1[0], r2[0])
        np.testing.assert_array_equal(r1[1], r2[1])

    def test_value_range_clipped(self, rng):
        img = rng.random((64, 64, 3), dtype=np.float32)
        mask = np.zeros((64, 64), dtype=np.uint8)
        img_out, _ = augment_patch(img, mask, rng=rng)
        assert img_out.min() >= 0.0
        assert img_out.max() <= 1.0


class TestTrainValTestSplit:
    def test_sizes(self, rng):
        X = rng.random((100, 32, 32, 3), dtype=np.float32)
        y = rng.integers(0, 2, (100, 32, 32)).astype(np.uint8)
        X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
        assert X_train.shape[0] + X_val.shape[0] + X_test.shape[0] == 100
        assert y_train.shape[0] + y_val.shape[0] + y_test.shape[0] == 100

    def test_no_leakage(self, rng):
        X = rng.random((100, 8, 8, 3), dtype=np.float32)
        y = rng.integers(0, 2, (100, 8, 8)).astype(np.uint8)
        X_train, X_val, X_test, _, _, _ = train_val_test_split(X, y)
        sets = [
            set(map(tuple, X_train.reshape(X_train.shape[0], -1))),
            set(map(tuple, X_val.reshape(X_val.shape[0], -1))),
            set(map(tuple, X_test.reshape(X_test.shape[0], -1))),
        ]
        assert sets[0].isdisjoint(sets[1])
        assert sets[0].isdisjoint(sets[2])
        assert sets[1].isdisjoint(sets[2])

    def test_default_fractions(self, rng):
        X = rng.random((100, 8, 8, 3), dtype=np.float32)
        y = rng.integers(0, 2, (100, 8, 8)).astype(np.uint8)
        X_train, X_val, X_test, _, _, _ = train_val_test_split(X, y)
        # 70/15/15 with ±1 rounding tolerance
        assert abs(X_train.shape[0] - 70) <= 1
        assert abs(X_val.shape[0] - 15) <= 2
        assert abs(X_test.shape[0] - 15) <= 2
