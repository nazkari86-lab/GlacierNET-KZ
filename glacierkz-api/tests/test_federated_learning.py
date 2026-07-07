"""
Tests for src.federated_learning
"""



class TestFederatedConfig:
    """Tests for FederatedConfig."""

    def test_import(self):
        from src.federated_learning import FederatedConfig
        assert FederatedConfig is not None

    def test_initialization(self):
        from src.federated_learning import FederatedConfig
        config = FederatedConfig(num_clients=10, rounds=20)
        assert config.num_clients == 10
        assert config.rounds == 20

    def test_defaults(self):
        from src.federated_learning import FederatedConfig
        config = FederatedConfig()
        assert config.num_clients == 5
        assert config.local_epochs == 5
        assert config.aggregation_strategy == "fedavg"

    def test_dp_config(self):
        from src.federated_learning import FederatedConfig
        config = FederatedConfig(differential_privacy=True, dp_epsilon=0.5)
        assert config.differential_privacy is True
        assert config.dp_epsilon == 0.5


class TestFederatedClient:
    """Tests for FederatedClient."""

    def test_import(self):
        from src.federated_learning import FederatedClient
        assert FederatedClient is not None

    def test_initialization(self):
        import tensorflow as tf

        from src.federated_learning import FederatedClient, FederatedConfig
        config = FederatedConfig()
        model = tf.keras.Sequential([tf.keras.layers.Dense(10)])
        client = FederatedClient(client_id=0, model=model, config=config)
        assert client.client_id == 0


class TestFederatedServer:
    """Tests for FederatedServer."""

    def test_import(self):
        from src.federated_learning import FederatedServer
        assert FederatedServer is not None

    def test_initialization(self):
        import tensorflow as tf

        from src.federated_learning import FederatedConfig, FederatedServer
        config = FederatedConfig()
        model = tf.keras.Sequential([tf.keras.layers.Dense(10)])
        server = FederatedServer(config=config, global_model=model)
        assert server is not None


class TestWeightAggregator:
    """Tests for WeightAggregator."""

    def test_import(self):
        from src.federated_learning import WeightAggregator
        assert WeightAggregator is not None

    def test_initialization(self):
        from src.federated_learning import WeightAggregator
        agg = WeightAggregator(strategy="fedavg")
        assert agg.strategy == "fedavg"

    def test_strategies(self):
        from src.federated_learning import WeightAggregator
        agg_avg = WeightAggregator(strategy="fedavg")
        agg_trim = WeightAggregator(strategy="trimmed_mean")
        agg_krum = WeightAggregator(strategy="krum")
        assert agg_avg.strategy == "fedavg"
        assert agg_trim.strategy == "trimmed_mean"
        assert agg_krum.strategy == "krum"


class TestDifferentialPrivacy:
    """Tests for DifferentialPrivacy."""

    def test_import(self):
        from src.federated_learning import DifferentialPrivacy
        assert DifferentialPrivacy is not None

    def test_initialization(self):
        from src.federated_learning import DifferentialPrivacy
        dp = DifferentialPrivacy(epsilon=1.0, delta=1e-5)
        assert dp.epsilon == 1.0
        assert dp.delta == 1e-5

    def test_default_params(self):
        from src.federated_learning import DifferentialPrivacy
        dp = DifferentialPrivacy()
        assert dp.epsilon == 1.0
        assert dp.max_norm == 1.0


class TestFederatedLearningManager:
    """Tests for FederatedLearningManager."""

    def test_import(self):
        from src.federated_learning import FederatedLearningManager
        assert FederatedLearningManager is not None

    def test_initialization(self):
        import tensorflow as tf

        from src.federated_learning import FederatedConfig, FederatedLearningManager
        config = FederatedConfig(num_clients=3, rounds=5)
        model = tf.keras.Sequential([tf.keras.layers.Dense(10)])
        manager = FederatedLearningManager(config=config, global_model=model)
        assert manager is not None

    def test_config_access(self):
        import tensorflow as tf

        from src.federated_learning import FederatedConfig, FederatedLearningManager
        config = FederatedConfig(num_clients=3, rounds=5)
        model = tf.keras.Sequential([tf.keras.layers.Dense(10)])
        manager = FederatedLearningManager(config=config, global_model=model)
        assert manager.config.num_clients == 3
