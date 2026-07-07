"""
Tests for src.self_supervised
"""



class TestSelfSupervisedConfig:
    """Tests for SelfSupervisedConfig."""

    def test_import(self):
        from src.self_supervised import SelfSupervisedConfig
        assert SelfSupervisedConfig is not None

    def test_initialization(self):
        from src.self_supervised import SelfSupervisedConfig
        config = SelfSupervisedConfig(method="simclr", temperature=0.1)
        assert config.method == "simclr"
        assert config.temperature == 0.1

    def test_defaults(self):
        from src.self_supervised import SelfSupervisedConfig
        config = SelfSupervisedConfig()
        assert config.method == "simclr"
        assert config.momentum == 0.999
        assert config.queue_size == 65536


class TestSimCLR:
    """Tests for SimCLR."""

    def test_import(self):
        from src.self_supervised import SimCLR
        assert SimCLR is not None

    def test_initialization(self):
        from src.self_supervised import SelfSupervisedConfig, SimCLR
        config = SelfSupervisedConfig(method="simclr")
        simclr = SimCLR(config)
        assert simclr is not None

    def test_config_access(self):
        from src.self_supervised import SelfSupervisedConfig, SimCLR
        config = SelfSupervisedConfig(method="simclr", temperature=0.1)
        simclr = SimCLR(config)
        assert simclr.config.temperature == 0.1


class TestBYOL:
    """Tests for BYOL."""

    def test_import(self):
        from src.self_supervised import BYOL
        assert BYOL is not None

    def test_initialization(self):
        from src.self_supervised import BYOL, SelfSupervisedConfig
        config = SelfSupervisedConfig(method="byol")
        byol = BYOL(config)
        assert byol is not None

    def test_momentum_config(self):
        from src.self_supervised import BYOL, SelfSupervisedConfig
        config = SelfSupervisedConfig(method="byol", momentum=0.99)
        byol = BYOL(config)
        assert byol.config.momentum == 0.99


class TestMoCo:
    """Tests for MoCo."""

    def test_import(self):
        from src.self_supervised import MoCo
        assert MoCo is not None

    def test_initialization(self):
        from src.self_supervised import MoCo, SelfSupervisedConfig
        config = SelfSupervisedConfig(method="moco")
        moco = MoCo(config)
        assert moco is not None

    def test_queue_size(self):
        from src.self_supervised import MoCo, SelfSupervisedConfig
        config = SelfSupervisedConfig(method="moco", queue_size=1024)
        moco = MoCo(config)
        assert moco.config.queue_size == 1024


class TestAugmentationConfig:
    """Tests for AugmentationConfig."""

    def test_import(self):
        from src.self_supervised import AugmentationConfig
        assert AugmentationConfig is not None

    def test_initialization(self):
        from src.self_supervised import AugmentationConfig
        config = AugmentationConfig()
        assert config is not None


class TestAugmentationPipeline:
    """Tests for AugmentationPipeline."""

    def test_import(self):
        from src.self_supervised import AugmentationPipeline
        assert AugmentationPipeline is not None

    def test_initialization(self):
        from src.self_supervised import AugmentationConfig, AugmentationPipeline
        config = AugmentationConfig()
        pipeline = AugmentationPipeline(config, input_shape=(64, 64, 11))
        assert pipeline is not None


class TestSelfSupervisedManager:
    """Tests for SelfSupervisedManager."""

    def test_import(self):
        from src.self_supervised import SelfSupervisedManager
        assert SelfSupervisedManager is not None

    def test_initialization(self):
        from src.self_supervised import SelfSupervisedConfig, SelfSupervisedManager
        config = SelfSupervisedConfig(method="simclr")
        manager = SelfSupervisedManager(config)
        assert manager is not None

    def test_has_build(self):
        from src.self_supervised import SelfSupervisedConfig, SelfSupervisedManager
        config = SelfSupervisedConfig(method="simclr")
        manager = SelfSupervisedManager(config)
        assert hasattr(manager, "build")

    def test_has_get_encoder(self):
        from src.self_supervised import SelfSupervisedConfig, SelfSupervisedManager
        config = SelfSupervisedConfig(method="simclr")
        manager = SelfSupervisedManager(config)
        assert hasattr(manager, "get_encoder")

    def test_has_pretrain(self):
        from src.self_supervised import SelfSupervisedConfig, SelfSupervisedManager
        config = SelfSupervisedConfig(method="simclr")
        manager = SelfSupervisedManager(config)
        assert hasattr(manager, "pretrain")
