# -*- coding: utf-8 -*-
"""Graph Neural Network for glacier connectivity analysis.

Implements message passing, graph convolution, and node classification
for analyzing spatial connectivity between glacier fragments and their
surrounding terrain features.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "GNNConfig",
    "build_adjacency_matrix",
    "graph_convolution",
    "message_passing",
    "build_gnn_model",
    "train_gnn",
    "evaluate_gnn",
    "glacier_graph_from_patches",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class GNNConfig:
    """Configuration for Graph Neural Network."""

    node_features: int = 32
    hidden_dim: int = 64
    num_classes: int = 3  # glacier, rock, vegetation
    num_layers: int = 3
    dropout_rate: float = 0.2
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    aggregator: str = "mean"  # mean, max, sum
    use_layer_norm: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.num_layers < 1:
            errors.append("num_layers must be >= 1")
        if self.aggregator not in ("mean", "max", "sum"):
            errors.append(f"Unknown aggregator: {self.aggregator}")
        return errors


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------


def build_adjacency_matrix(
    edge_index: np.ndarray,
    num_nodes: int,
    add_self_loops: bool = True,
) -> np.ndarray:
    """Build adjacency matrix from edge index pairs.

    Args:
        edge_index: Array of shape (2, num_edges) with source and target indices.
        num_nodes: Total number of nodes.
        add_self_loops: Whether to add self-loop edges.

    Returns:
        Sparse-like adjacency matrix as dense numpy array of shape (N, N).
    """
    adj = np.zeros((num_nodes, num_nodes), dtype=np.float32)

    src, dst = edge_index[0], edge_index[1]
    adj[src, dst] = 1.0

    # Symmetric normalization: D^{-1/2} A D^{-1/2}
    degree = adj.sum(axis=1, keepdims=True)
    degree = np.maximum(degree, 1.0)
    d_inv_sqrt = 1.0 / np.sqrt(degree)
    adj_norm = adj * d_inv_sqrt * d_inv_sqrt.T

    if add_self_loops:
        adj_norm += np.eye(num_nodes, dtype=np.float32)

    return adj_norm


def glacier_graph_from_patches(
    patch_grid: np.ndarray,
    patch_size: int = 256,
    threshold: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Construct a graph from a grid of satellite image patches.

    Nodes represent patches; edges connect spatially adjacent patches.
    Node features are computed from patch spectral statistics.

    Args:
        patch_grid: Array of shape (H, W, C) representing the full mosaic.
        patch_size: Spatial size of each patch.
        threshold: Glacier probability threshold for labeling.

    Returns:
        Tuple of (node_features, edge_index, labels).
    """
    h, w = patch_grid.shape[:2]
    n_rows = h // patch_size
    n_cols = w // patch_size
    num_nodes = n_rows * n_cols
    num_channels = patch_grid.shape[-1]

    # Node features: spectral statistics per patch
    node_features = np.zeros((num_nodes, num_channels * 3), dtype=np.float32)
    labels = np.zeros(num_nodes, dtype=np.int32)

    for r in range(n_rows):
        for c in range(n_cols):
            idx = r * n_cols + c
            patch = patch_grid[
                r * patch_size : (r + 1) * patch_size,
                c * patch_size : (c + 1) * patch_size,
            ]
            # Feature extraction: mean, std, max per channel
            node_features[idx, :num_channels] = patch.mean(axis=(0, 1))
            node_features[idx, num_channels : 2 * num_channels] = patch.std(axis=(0, 1))
            node_features[idx, 2 * num_channels : 3 * num_channels] = patch.max(axis=(0, 1))

            # Label: 0=background, 1=glacier, 2=mixed
            glacier_fraction = (patch.mean(axis=-1) > threshold).mean()
            if glacier_fraction > 0.7:
                labels[idx] = 1
            elif glacier_fraction > 0.2:
                labels[idx] = 2

    # Edges: 4-connectivity grid graph
    edges_src, edges_dst = [], []
    for r in range(n_rows):
        for c in range(n_cols):
            idx = r * n_cols + c
            if c + 1 < n_cols:
                edges_src.extend([idx, idx + 1])
                edges_dst.extend([idx + 1, idx])
            if r + 1 < n_rows:
                edges_src.extend([idx, idx + n_cols])
                edges_dst.extend([idx + n_cols, idx])

    edge_index = np.array([edges_src, edges_dst], dtype=np.int64)
    return node_features, edge_index, labels


# ---------------------------------------------------------------------------
# Graph Convolution Layer
# ---------------------------------------------------------------------------


def graph_convolution(features, adj, out_dim: int, use_layer_norm: bool = True):
    """Graph Convolutional Network (GCN) layer.

    Implements: H' = σ(D̃^{-1/2} Ã D̃^{-1/2} H W)

    Args:
        features: Node feature matrix of shape (N, F_in).
        adj: Normalized adjacency matrix of shape (N, N).
        out_dim: Output feature dimension.
        use_layer_norm: Whether to apply layer normalization.

    Returns:
        Updated node features of shape (N, out_dim).
    """
    import tensorflow as tf

    in_dim = features.shape[-1]
    weight = tf.Variable(tf.random.normal((in_dim, out_dim), stddev=0.01), name="gcn_weight")

    # Propagate: A @ H @ W
    support = tf.matmul(features, weight)
    output = tf.matmul(adj, support)

    if use_layer_norm:
        output = tf.keras.layers.LayerNormalization(epsilon=1e-6)(output)

    output = tf.nn.relu(output)
    return output


# ---------------------------------------------------------------------------
# Message Passing
# ---------------------------------------------------------------------------


def message_passing(
    node_features: np.ndarray,
    edge_index: np.ndarray,
    num_nodes: int,
    out_dim: int,
    aggregator: str = "mean",
    activation: str = "relu",
):
    """General message passing layer.

    Each node aggregates messages from neighbors, then applies a transform.

    Args:
        node_features: Current node features (N, F_in).
        edge_index: Edge indices (2, E).
        num_nodes: Number of nodes.
        out_dim: Output feature dimension.
        aggregator: Aggregation function (mean, max, sum).
        activation: Activation function name.

    Returns:
        Updated node features (N, out_dim).
    """
    import tensorflow as tf

    f_in = node_features.shape[-1]
    w_msg = tf.Variable(tf.random.normal((f_in, out_dim), stddev=0.01), name="msg_weight")
    w_agg = tf.Variable(tf.random.normal((out_dim, out_dim), stddev=0.01), name="agg_weight")

    src, dst = edge_index[0], edge_index[1]

    # Compute messages
    messages = tf.matmul(tf.gather(node_features, src), w_msg)

    # Aggregate messages per destination node
    aggregated = tf.math.unsorted_segment_mean(
        messages,
        tf.cast(dst, tf.int32),
        num_segments=num_nodes,
    )

    # Transform aggregated messages
    output = tf.matmul(aggregated, w_agg)

    if activation == "relu":
        output = tf.nn.relu(output)
    elif activation == "gelu":
        output = tf.nn.gelu(output)

    return output


# ---------------------------------------------------------------------------
# Full GNN Model
# ---------------------------------------------------------------------------


def build_gnn_model(config: GNNConfig):
    """Build a Graph Neural Network model using Keras functional API.

    Args:
        config: GNN configuration.

    Returns:
        Keras Model instance.
    """
    import tensorflow as tf

    features_input = tf.keras.Input(shape=(None, config.node_features), name="node_features")
    adj_input = tf.keras.Input(shape=(None, None), name="adjacency")

    h = features_input

    for i in range(config.num_layers):
        dim = config.hidden_dim if i < config.num_layers - 1 else config.num_classes
        use_ln = config.use_layer_norm if i < config.num_layers - 1 else False

        h_prev = h
        h = tf.keras.layers.Dense(dim, use_bias=False, name=f"gcn_dense_{i}")(h)
        h = tf.keras.layers.Lambda(lambda tensors: tf.matmul(tensors[0], tensors[1]), name=f"gcn_propagate_{i}")(
            [adj_input, h]
        )

        if use_ln:
            h = tf.keras.layers.LayerNormalization(epsilon=1e-6)(h)

        h = tf.keras.layers.Activation("relu")(h)

        if config.dropout_rate > 0 and i < config.num_layers - 1:
            h = tf.keras.layers.Dropout(config.dropout_rate)(h)

        # Residual connection if dimensions match
        if h_prev.shape[-1] == dim:
            h = tf.keras.layers.Add()([h, h_prev])

    model = tf.keras.Model(
        inputs=[features_input, adj_input],
        outputs=h,
        name="gnn_classifier",
    )
    return model


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_gnn(
    model,
    features: np.ndarray,
    adj: np.ndarray,
    labels: np.ndarray,
    train_mask: np.ndarray,
    val_mask: np.ndarray,
    config: GNNConfig,
    epochs: int = 200,
    save_path: str = "models/gnn_best.weights.h5",
):
    """Train the GNN model with full-graph training.

    Args:
        model: GNN Keras model.
        features: Node features (N, F).
        adj: Adjacency matrix (N, N).
        labels: Node labels (N,).
        train_mask: Boolean mask for training nodes.
        val_mask: Boolean mask for validation nodes.
        config: GNN configuration.
        epochs: Number of training epochs.
        save_path: Path to save best model weights.

    Returns:
        Training history dictionary.
    """
    from pathlib import Path

    import tensorflow as tf

    features_t = tf.constant(features, dtype=tf.float32)
    adj_t = tf.constant(adj, dtype=tf.float32)
    labels_t = tf.constant(labels, dtype=tf.int32)

    optimizer = tf.keras.optimizers.Adam(
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    best_val_acc = 0.0
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    for epoch in range(epochs):
        with tf.GradientTape() as tape:
            logits = model([features_t, adj_t], training=True)
            logits_train = tf.boolean_mask(logits, train_mask)
            labels_train = tf.boolean_mask(labels_t, train_mask)
            loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels_train, logits_train)

            # Weight decay
            l2_loss = sum(tf.nn.l2_loss(v) for v in model.trainable_variables if "kernel" in v.name)
            loss = tf.reduce_mean(loss) + config.weight_decay * l2_loss

        grads = tape.gradient(loss, model.trainable_variables)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))

        # Compute metrics
        logits_full = model([features_t, adj_t], training=False)
        train_preds = tf.argmax(tf.boolean_mask(logits_full, train_mask), axis=-1)
        val_preds = tf.argmax(tf.boolean_mask(logits_full, val_mask), axis=-1)
        train_acc = tf.reduce_mean(tf.cast(tf.equal(train_preds, tf.boolean_mask(labels_t, train_mask)), tf.float32))
        val_acc = tf.reduce_mean(tf.cast(tf.equal(val_preds, tf.boolean_mask(labels_t, val_mask)), tf.float32))

        history["train_loss"].append(float(loss))
        history["train_acc"].append(float(train_acc))
        history["val_acc"].append(float(val_acc))

        if val_acc > best_val_acc:
            best_val_acc = float(val_acc)
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            model.save_weights(save_path)

        if (epoch + 1) % 20 == 0:
            logger.info(
                "Epoch %d — loss: %.4f, train_acc: %.4f, val_acc: %.4f (best: %.4f)",
                epoch + 1,
                float(loss),
                float(train_acc),
                float(val_acc),
                best_val_acc,
            )

    return history


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_gnn(model, features, adj, labels, test_mask):
    """Evaluate GNN on test nodes.

    Args:
        model: Trained GNN model.
        features: Node features.
        adj: Adjacency matrix.
        labels: True labels.
        test_mask: Boolean mask for test nodes.

    Returns:
        Dictionary with accuracy and per-class metrics.
    """
    import tensorflow as tf

    features_t = tf.constant(features, dtype=tf.float32)
    adj_t = tf.constant(adj, dtype=tf.float32)

    logits = model([features_t, adj_t], training=False)
    test_logits = tf.boolean_mask(logits, test_mask)
    test_labels = tf.boolean_mask(tf.constant(labels, dtype=tf.int32), test_mask)

    preds = tf.argmax(test_logits, axis=-1)
    accuracy = float(tf.reduce_mean(tf.cast(tf.equal(preds, test_labels), tf.float32)))

    # Per-class precision and recall
    num_classes = max(labels.max() + 1, 2)
    per_class = {}
    for c in range(num_classes):
        c_mask = test_labels == c
        if tf.reduce_sum(tf.cast(c_mask, tf.float32)) > 0:
            c_preds = preds[c_mask]
            precision = float(tf.reduce_mean(tf.cast(c_preds == c, tf.float32)))
            recall = float(tf.reduce_sum(tf.cast(tf.equal(preds[c_mask], c), tf.float32))) / max(
                float(tf.reduce_sum(tf.cast(c_mask, tf.float32))), 1.0
            )
            f1 = 2 * precision * recall / max(precision + recall, 1e-8)
            per_class[f"class_{c}"] = {"precision": precision, "recall": recall, "f1": f1}

    return {"accuracy": accuracy, "per_class": per_class}
