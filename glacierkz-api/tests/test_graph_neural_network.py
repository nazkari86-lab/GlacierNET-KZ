"""
Tests for src.graph_neural_network
"""

import pytest

pytestmark = pytest.mark.experimental



class TestGNNConfig:
    """Tests for GNNConfig."""

    def test_import(self):
        from src.graph_neural_network import GNNConfig
        assert GNNConfig is not None

    def test_initialization(self):
        from src.graph_neural_network import GNNConfig
        config = GNNConfig(node_features=32, hidden_dim=64, num_classes=2)
        assert config.node_features == 32
        assert config.hidden_dim == 64

    def test_defaults(self):
        from src.graph_neural_network import GNNConfig
        config = GNNConfig()
        assert config.node_features == 32
        assert config.num_layers == 3
        assert config.aggregator == "mean"


class TestBuildGNNModel:
    """Tests for build_gnn_model."""

    def test_import(self):
        from src.graph_neural_network import build_gnn_model
        assert build_gnn_model is not None

    def test_build_model(self):
        from src.graph_neural_network import GNNConfig, build_gnn_model
        config = GNNConfig(node_features=16, hidden_dim=32, num_classes=2, num_layers=2)
        model = build_gnn_model(config)
        assert model is not None


class TestGraphConvolution:
    """Tests for graph_convolution."""

    def test_import(self):
        from src.graph_neural_network import graph_convolution
        assert callable(graph_convolution)

    def test_message_passing(self):
        from src.graph_neural_network import message_passing
        assert callable(message_passing)


class TestBuildAdjacencyMatrix:
    """Tests for build_adjacency_matrix."""

    def test_import(self):
        from src.graph_neural_network import build_adjacency_matrix
        assert callable(build_adjacency_matrix)

    def test_build_matrix(self):
        import numpy as np

        from src.graph_neural_network import build_adjacency_matrix
        edge_index = np.array([[0, 1, 1, 2], [1, 0, 2, 1]])
        adj = build_adjacency_matrix(edge_index, num_nodes=3)
        assert adj.shape == (3, 3)


class TestGlacierGraphFromPatches:
    """Tests for glacier_graph_from_patches."""

    def test_import(self):
        from src.graph_neural_network import glacier_graph_from_patches
        assert callable(glacier_graph_from_patches)


class TestTrainGNN:
    """Tests for train_gnn."""

    def test_import(self):
        from src.graph_neural_network import train_gnn
        assert callable(train_gnn)


class TestEvaluateGNN:
    """Tests for evaluate_gnn."""

    def test_import(self):
        from src.graph_neural_network import evaluate_gnn
        assert callable(evaluate_gnn)
