"""
Tests for src.distributed_training
"""



class TestDistributedConfig:
    """Tests for DistributedConfig."""

    def test_import(self):
        from src.distributed_training import DistributedConfig
        assert DistributedConfig is not None

    def test_initialization(self):
        from src.distributed_training import DistributedConfig
        config = DistributedConfig(num_workers=4, gradient_accumulation_steps=8)
        assert config.num_workers == 4
        assert config.gradient_accumulation_steps == 8

    def test_defaults(self):
        from src.distributed_training import DistributedConfig
        config = DistributedConfig()
        assert config.num_workers == 2
        assert config.strategy == "data_parallel"
        assert config.all_reduce_algorithm == "ring"
        assert config.compression == "none"


class TestGradientAccumulator:
    """Tests for GradientAccumulator."""

    def test_import(self):
        from src.distributed_training import GradientAccumulator
        assert GradientAccumulator is not None

    def test_initialization(self):
        import tensorflow as tf

        from src.distributed_training import GradientAccumulator
        model = tf.keras.Sequential([tf.keras.layers.Dense(10)])
        acc = GradientAccumulator(model, accumulation_steps=4)
        assert acc is not None

    def test_attributes(self):
        import tensorflow as tf

        from src.distributed_training import GradientAccumulator
        model = tf.keras.Sequential([tf.keras.layers.Dense(10)])
        acc = GradientAccumulator(model, accumulation_steps=8)
        assert hasattr(acc, "accumulation_steps") or hasattr(acc, "accumulated_gradients")


class TestGradientCompressor:
    """Tests for GradientCompressor."""

    def test_import(self):
        from src.distributed_training import GradientCompressor
        assert GradientCompressor is not None

    def test_initialization(self):
        from src.distributed_training import GradientCompressor
        comp = GradientCompressor(algorithm="top_k")
        assert comp.algorithm == "top_k"

    def test_algorithms(self):
        from src.distributed_training import GradientCompressor
        comp_none = GradientCompressor(algorithm="none")
        comp_topk = GradientCompressor(algorithm="top_k")
        comp_random = GradientCompressor(algorithm="random_k")
        assert comp_none.algorithm == "none"
        assert comp_topk.algorithm == "top_k"
        assert comp_random.algorithm == "random_k"


class TestGradientAllReducer:
    """Tests for GradientAllReducer."""

    def test_import(self):
        from src.distributed_training import GradientAllReducer
        assert GradientAllReducer is not None

    def test_initialization(self):
        from src.distributed_training import GradientAllReducer
        reducer = GradientAllReducer(algorithm="ring")
        assert reducer.algorithm == "ring"

    def test_algorithms(self):
        from src.distributed_training import GradientAllReducer
        reducer_ring = GradientAllReducer(algorithm="ring")
        reducer_tree = GradientAllReducer(algorithm="tree")
        assert reducer_ring.algorithm == "ring"
        assert reducer_tree.algorithm == "tree"


class TestDistributedTrainer:
    """Tests for DistributedTrainer."""

    def test_import(self):
        from src.distributed_training import DistributedTrainer
        assert DistributedTrainer is not None

    def test_initialization(self):
        import tensorflow as tf

        from src.distributed_training import DistributedConfig, DistributedTrainer
        config = DistributedConfig(num_workers=2)
        model = tf.keras.Sequential([tf.keras.layers.Dense(10)])
        trainer = DistributedTrainer(config=config, global_model=model)
        assert trainer is not None

    def test_config_access(self):
        import tensorflow as tf

        from src.distributed_training import DistributedConfig, DistributedTrainer
        config = DistributedConfig(num_workers=4, mixed_precision=True)
        model = tf.keras.Sequential([tf.keras.layers.Dense(10)])
        trainer = DistributedTrainer(config=config, global_model=model)
        assert trainer.config.num_workers == 4
        assert trainer.config.mixed_precision is True


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor."""

    def test_import(self):
        from src.distributed_training import PerformanceMonitor
        assert PerformanceMonitor is not None

    def test_initialization(self):
        from src.distributed_training import PerformanceMonitor
        monitor = PerformanceMonitor()
        assert monitor is not None

    def test_has_methods(self):
        from src.distributed_training import PerformanceMonitor
        monitor = PerformanceMonitor()
        assert hasattr(monitor, "record_step")
        assert hasattr(monitor, "record_communication")
        assert hasattr(monitor, "compute_throughput")
        assert hasattr(monitor, "get_summary")
