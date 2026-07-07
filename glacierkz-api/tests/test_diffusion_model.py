"""
Tests for src.diffusion_model
"""



class TestDiffusionConfig:
    """Tests for DiffusionConfig."""

    def test_import(self):
        from src.diffusion_model import DiffusionConfig
        assert DiffusionConfig is not None

    def test_initialization(self):
        from src.diffusion_model import DiffusionConfig
        config = DiffusionConfig(image_size=64, timesteps=100, base_channels=32)
        assert config.image_size == 64
        assert config.timesteps == 100
        assert config.base_channels == 32

    def test_defaults(self):
        from src.diffusion_model import DiffusionConfig
        config = DiffusionConfig()
        assert config.image_size == 256
        assert config.timesteps == 1000
        assert config.beta_start == 0.0001
        assert config.beta_end == 0.02

    def test_schedule_types(self):
        from src.diffusion_model import DiffusionConfig
        config = DiffusionConfig(schedule_type="cosine")
        assert config.schedule_type == "cosine"


class TestGetNoiseSchedule:
    """Tests for get_noise_schedule."""

    def test_import(self):
        from src.diffusion_model import get_noise_schedule
        assert callable(get_noise_schedule)

    def test_linear_schedule(self):
        from src.diffusion_model import DiffusionConfig, get_noise_schedule
        config = DiffusionConfig(timesteps=100, schedule_type="linear")
        result = get_noise_schedule(config)
        assert "betas" in result
        assert len(result["betas"]) == 100
        assert result["betas"][0] < result["betas"][-1]

    def test_cosine_schedule(self):
        from src.diffusion_model import DiffusionConfig, get_noise_schedule
        config = DiffusionConfig(timesteps=100, schedule_type="cosine")
        result = get_noise_schedule(config)
        assert "betas" in result
        assert len(result["betas"]) == 100


class TestForwardDiffusion:
    """Tests for forward_diffusion."""

    def test_import(self):
        from src.diffusion_model import forward_diffusion
        assert callable(forward_diffusion)


class TestBuildUNet:
    """Tests for build_unet."""

    def test_import(self):
        from src.diffusion_model import build_unet
        assert callable(build_unet)


class TestSampleDDPM:
    """Tests for sample_ddpm."""

    def test_import(self):
        from src.diffusion_model import sample_ddpm
        assert callable(sample_ddpm)


class TestBuildAndTrainDiffusion:
    """Tests for build_and_train_diffusion."""

    def test_import(self):
        from src.diffusion_model import build_and_train_diffusion
        assert callable(build_and_train_diffusion)


class TestBuildSuperResDiffusion:
    """Tests for build_super_res_diffusion."""

    def test_import(self):
        from src.diffusion_model import build_super_res_diffusion
        assert callable(build_super_res_diffusion)


class TestTrainDiffusionStep:
    """Tests for train_diffusion_step."""

    def test_import(self):
        from src.diffusion_model import train_diffusion_step
        assert callable(train_diffusion_step)
