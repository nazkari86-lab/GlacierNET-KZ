"""
Tests for src.active_learning
"""



class TestActiveLearningConfig:
    """Tests for ActiveLearningConfig."""

    def test_import(self):
        from src.active_learning import ActiveLearningConfig
        assert ActiveLearningConfig is not None

    def test_initialization(self):
        from src.active_learning import ActiveLearningConfig, QueryStrategy
        config = ActiveLearningConfig(strategy=QueryStrategy.UNCERTAINTY, query_batch_size=10)
        assert config.strategy == QueryStrategy.UNCERTAINTY
        assert config.query_batch_size == 10

    def test_defaults(self):
        from src.active_learning import ActiveLearningConfig
        config = ActiveLearningConfig()
        assert config.initial_labeled == 50
        assert config.max_iterations == 50
        assert config.num_committee == 5


class TestQueryStrategy:
    """Tests for QueryStrategy enum."""

    def test_import(self):
        from src.active_learning import QueryStrategy
        assert QueryStrategy is not None

    def test_values(self):
        from src.active_learning import QueryStrategy
        assert hasattr(QueryStrategy, "UNCERTAINTY")
        assert hasattr(QueryStrategy, "MARGIN")
        assert hasattr(QueryStrategy, "ENTROPY")
        assert hasattr(QueryStrategy, "COMMITTEE")
        assert hasattr(QueryStrategy, "DENSITY")


class TestAnnotationBudget:
    """Tests for AnnotationBudget."""

    def test_import(self):
        from src.active_learning import AnnotationBudget
        assert AnnotationBudget is not None

    def test_initialization(self):
        from src.active_learning import AnnotationBudget
        budget = AnnotationBudget(total_budget=100, cost_per_sample=1.0)
        assert budget.total_budget == 100
        assert budget.used == 0

    def test_can_annotate(self):
        from src.active_learning import AnnotationBudget
        budget = AnnotationBudget(total_budget=10, used=5)
        assert budget.remaining >= 0

    def test_remaining(self):
        from src.active_learning import AnnotationBudget
        budget = AnnotationBudget(total_budget=100, used=30)
        assert budget.remaining == 70


class TestActiveLearningLoop:
    """Tests for ActiveLearningLoop."""

    def test_import(self):
        from src.active_learning import ActiveLearningLoop
        assert ActiveLearningLoop is not None

    def test_initialization(self):
        from src.active_learning import ActiveLearningConfig, ActiveLearningLoop
        config = ActiveLearningConfig()
        loop = ActiveLearningLoop(config)
        assert loop is not None

    def test_with_budget(self):
        from src.active_learning import ActiveLearningConfig, ActiveLearningLoop, AnnotationBudget
        config = ActiveLearningConfig()
        budget = AnnotationBudget(total_budget=100)
        loop = ActiveLearningLoop(config, budget=budget)
        assert loop is not None


class TestQueryFunctions:
    """Tests for query sampling functions."""

    def test_uncertainty_sampling(self):
        from src.active_learning import uncertainty_sampling
        assert callable(uncertainty_sampling)

    def test_margin_sampling(self):
        from src.active_learning import margin_sampling
        assert callable(margin_sampling)

    def test_entropy_sampling(self):
        from src.active_learning import entropy_sampling
        assert callable(entropy_sampling)

    def test_query_by_committee(self):
        from src.active_learning import query_by_committee
        assert callable(query_by_committee)

    def test_density_weighted_sampling(self):
        from src.active_learning import density_weighted_sampling
        assert callable(density_weighted_sampling)

    def test_expected_gradient_length(self):
        from src.active_learning import expected_gradient_length
        assert callable(expected_gradient_length)
