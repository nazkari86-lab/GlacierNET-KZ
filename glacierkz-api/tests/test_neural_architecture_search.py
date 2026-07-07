"""
Tests for src.neural_architecture_search
"""



class TestNASConfig:
    """Tests for NASConfig."""

    def test_import(self):
        from src.neural_architecture_search import NASConfig
        assert NASConfig is not None

    def test_initialization(self):
        from src.neural_architecture_search import NASConfig
        config = NASConfig(population_size=10, generations=5)
        assert config.population_size == 10
        assert config.generations == 5

    def test_defaults(self):
        from src.neural_architecture_search import NASConfig
        config = NASConfig()
        assert config.search_space == "encoder_decoder"
        assert config.crossover_rate == 0.7
        assert config.mutation_rate == 0.3


class TestSearchSpace:
    """Tests for SearchSpace."""

    def test_import(self):
        from src.neural_architecture_search import SearchSpace
        assert SearchSpace is not None

    def test_initialization(self):
        from src.neural_architecture_search import NASConfig, SearchSpace
        config = NASConfig()
        ss = SearchSpace(config)
        assert ss is not None

    def test_random_architecture(self):
        from src.neural_architecture_search import NASConfig, SearchSpace
        config = NASConfig()
        ss = SearchSpace(config)
        arch = ss.random_architecture()
        assert arch is not None
        assert hasattr(arch, "genes")


class TestArchitecture:
    """Tests for Architecture."""

    def test_import(self):
        from src.neural_architecture_search import Architecture
        assert Architecture is not None

    def test_attributes(self):
        from src.neural_architecture_search import Architecture, ArchitectureGene
        gene = ArchitectureGene(
            cell_type="encoder", num_filters=32, kernel_size=3,
            num_repeats=1, use_se=False, use_attention=True,
            activation="relu", normalization="batch_norm",
            dropout_rate=0.1, residual=False, depthwise=False, dilated=False,
        )
        arch = Architecture(genes=[gene])
        assert hasattr(arch, "genes")
        assert hasattr(arch, "fitness")
        assert hasattr(arch, "num_params")
        assert hasattr(arch, "accuracy")


class TestEvolutionarySearch:
    """Tests for EvolutionarySearch."""

    def test_import(self):
        from src.neural_architecture_search import EvolutionarySearch
        assert EvolutionarySearch is not None

    def test_initialization(self):
        from src.neural_architecture_search import EvolutionarySearch, NASConfig
        config = NASConfig(population_size=10)
        es = EvolutionarySearch(config)
        assert es is not None

    def test_tournament_select(self):
        from src.neural_architecture_search import EvolutionarySearch, NASConfig
        config = NASConfig(population_size=10, tournament_size=3)
        es = EvolutionarySearch(config)
        assert hasattr(es, "tournament_select")

    def test_initialize_population(self):
        from src.neural_architecture_search import EvolutionarySearch, NASConfig
        config = NASConfig(population_size=10)
        es = EvolutionarySearch(config)
        assert hasattr(es, "initialize_population")

    def test_evolve_generation(self):
        from src.neural_architecture_search import EvolutionarySearch, NASConfig
        config = NASConfig(population_size=10)
        es = EvolutionarySearch(config)
        assert hasattr(es, "evolve_generation")


class TestWeightSharingEstimator:
    """Tests for WeightSharingEstimator."""

    def test_import(self):
        from src.neural_architecture_search import WeightSharingEstimator
        assert WeightSharingEstimator is not None

    def test_initialization(self):
        from src.neural_architecture_search import NASConfig, WeightSharingEstimator
        config = NASConfig()
        wse = WeightSharingEstimator(config)
        assert wse is not None

    def test_estimate_methods(self):
        from src.neural_architecture_search import NASConfig, WeightSharingEstimator
        config = NASConfig()
        wse = WeightSharingEstimator(config)
        assert hasattr(wse, "compute_fitness")
        assert hasattr(wse, "estimate_parameters")
        assert hasattr(wse, "estimate_flops")
        assert hasattr(wse, "estimate_inference_time")


class TestNASManager:
    """Tests for NASManager."""

    def test_import(self):
        from src.neural_architecture_search import NASManager
        assert NASManager is not None

    def test_initialization(self):
        from src.neural_architecture_search import NASConfig, NASManager
        config = NASConfig()
        manager = NASManager(config)
        assert manager is not None

    def test_search_space(self):
        from src.neural_architecture_search import NASConfig, NASManager
        config = NASConfig()
        manager = NASManager(config)
        assert hasattr(manager, "search_space")
