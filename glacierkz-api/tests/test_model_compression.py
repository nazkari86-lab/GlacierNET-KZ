"""
Tests for src.model_compression
"""



class TestCompressionConfig:
    """Tests for CompressionConfig."""

    def test_import(self):
        from src.model_compression import CompressionConfig
        assert CompressionConfig is not None

    def test_initialization(self):
        from src.model_compression import CompressionConfig
        config = CompressionConfig(pruning_sparsity=0.7, quantization_type="int8")
        assert config.pruning_sparsity == 0.7
        assert config.quantization_type == "int8"

    def test_defaults(self):
        from src.model_compression import CompressionConfig
        config = CompressionConfig()
        assert config.pruning is True
        assert config.quantization is True
        assert config.distillation is False
        assert config.pruning_sparsity == 0.5


class TestPruner:
    """Tests for Pruner."""

    def test_import(self):
        from src.model_compression import Pruner
        assert Pruner is not None

    def test_initialization(self):
        from src.model_compression import CompressionConfig, Pruner
        config = CompressionConfig(pruning_sparsity=0.5)
        pruner = Pruner(config)
        assert pruner is not None

    def test_attributes(self):
        from src.model_compression import CompressionConfig, Pruner
        config = CompressionConfig(pruning_sparsity=0.5, pruning_method="magnitude")
        pruner = Pruner(config)
        assert hasattr(pruner, "config")
        assert pruner.config.pruning_sparsity == 0.5


class TestQuantizer:
    """Tests for Quantizer."""

    def test_import(self):
        from src.model_compression import Quantizer
        assert Quantizer is not None

    def test_initialization(self):
        from src.model_compression import CompressionConfig, Quantizer
        config = CompressionConfig(quantization_type="int8")
        quantizer = Quantizer(config)
        assert quantizer is not None

    def test_attributes(self):
        from src.model_compression import CompressionConfig, Quantizer
        config = CompressionConfig(quantization_type="float16")
        quantizer = Quantizer(config)
        assert hasattr(quantizer, "config")


class TestKnowledgeDistiller:
    """Tests for KnowledgeDistiller."""

    def test_import(self):
        from src.model_compression import KnowledgeDistiller
        assert KnowledgeDistiller is not None

    def test_initialization(self):
        from src.model_compression import CompressionConfig, KnowledgeDistiller
        config = CompressionConfig(distillation_temperature=4.0, distillation_alpha=0.7)
        distiller = KnowledgeDistiller(config)
        assert distiller is not None

    def test_attributes(self):
        from src.model_compression import CompressionConfig, KnowledgeDistiller
        config = CompressionConfig(distillation_temperature=8.0)
        distiller = KnowledgeDistiller(config)
        assert hasattr(distiller, "config")


class TestModelCompressor:
    """Tests for ModelCompressor."""

    def test_import(self):
        from src.model_compression import ModelCompressor
        assert ModelCompressor is not None

    def test_initialization(self):
        from src.model_compression import CompressionConfig, ModelCompressor
        config = CompressionConfig()
        compressor = ModelCompressor(config)
        assert compressor is not None

    def test_attributes(self):
        from src.model_compression import CompressionConfig, ModelCompressor
        config = CompressionConfig()
        compressor = ModelCompressor(config)
        assert hasattr(compressor, "config")


class TestModelAnalyzer:
    """Tests for ModelAnalyzer."""

    def test_import(self):
        from src.model_compression import ModelAnalyzer
        assert ModelAnalyzer is not None

    def test_initialization(self):
        from src.model_compression import ModelAnalyzer
        analyzer = ModelAnalyzer()
        assert analyzer is not None

    def test_has_analyze(self):
        from src.model_compression import ModelAnalyzer
        analyzer = ModelAnalyzer()
        assert hasattr(analyzer, "analyze") or hasattr(analyzer, "compute_macs") or hasattr(analyzer, "get_model_stats")
