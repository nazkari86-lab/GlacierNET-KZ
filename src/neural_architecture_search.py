"""
Модуль нейронного поиска архитектур (NAS) для GlacierNET-KZ.

Реализует автоматический поиск архитектур с поддержкой:
- Пространства поиска (search space)
- Разделяемых весов (weight sharing)
- Прогнозирования производительности
- Эволюционного поиска
"""

import json
import logging
import os
import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class NASConfig:
    """Конфигурация NAS."""

    search_space: str = "encoder_decoder"
    num_cells: int = 6
    num_nodes_per_cell: int = 4
    max_depth: int = 5
    population_size: int = 20
    generations: int = 30
    tournament_size: int = 3
    crossover_rate: float = 0.7
    mutation_rate: float = 0.3
    num_architectures_to_evaluate: int = 50
    epochs_per_architecture: int = 5
    input_shapes: List[Tuple[int, ...]] = field(default_factory=lambda: [(256, 256, 3), (256, 256, 1)])
    num_classes: int = 1
    learning_rate: float = 1e-3
    batch_size: int = 8
    target_flops: float = 1e9
    target_params: int = 5e6
    checkpoint_dir: str = "checkpoints/nas"
    log_dir: str = "logs/nas"


@dataclass
class ArchitectureGene:
    """Ген архитектуры для NAS."""

    cell_type: str = "encoder"
    num_filters: int = 64
    kernel_size: int = 3
    num_repeats: int = 1
    use_se: bool = False
    use_attention: bool = False
    activation: str = "relu"
    normalization: str = "batch_norm"
    dropout_rate: float = 0.0
    residual: bool = False
    depthwise: bool = False
    dilated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_type": self.cell_type,
            "num_filters": self.num_filters,
            "kernel_size": self.kernel_size,
            "num_repeats": self.num_repeats,
            "use_se": self.use_se,
            "use_attention": self.use_attention,
            "activation": self.activation,
            "normalization": self.normalization,
            "dropout_rate": self.dropout_rate,
            "residual": self.residual,
            "depthwise": self.depthwise,
            "dilated": self.dilated,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ArchitectureGene":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Architecture:
    """Полная архитектура (список генов)."""

    genes: List[ArchitectureGene] = field(default_factory=list)
    fitness: float = 0.0
    num_params: int = 0
    flops: float = 0.0
    inference_time: float = 0.0
    accuracy: float = 0.0
    generation: int = 0
    architecture_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genes": [g.to_dict() for g in self.genes],
            "fitness": self.fitness,
            "num_params": self.num_params,
            "flops": self.flops,
            "inference_time": self.inference_time,
            "accuracy": self.accuracy,
            "generation": self.generation,
            "architecture_id": self.architecture_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Architecture":
        genes = [ArchitectureGene.from_dict(g) for g in d.get("genes", [])]
        return cls(
            genes=genes,
            fitness=d.get("fitness", 0.0),
            num_params=d.get("num_params", 0),
            flops=d.get("flops", 0.0),
            inference_time=d.get("inference_time", 0.0),
            accuracy=d.get("accuracy", 0.0),
            generation=d.get("generation", 0),
            architecture_id=d.get("architecture_id", ""),
        )


class SearchSpace:
    """Пространство поиска архитектур."""

    CELL_TYPES = ["encoder", "decoder", "bottleneck", "skip"]
    ACTIVATIONS = ["relu", "leaky_relu", "swish", "gelu"]
    NORMALIZATIONS = ["batch_norm", "layer_norm", "group_norm"]

    FILTER_SIZES = [16, 32, 48, 64, 96, 128, 192, 256]
    KERNEL_SIZES = [1, 3, 5, 7]
    DEPTHWISE_OPTIONS = [True, False]
    DILATED_OPTIONS = [True, False]
    RESIDUAL_OPTIONS = [True, False]
    SE_OPTIONS = [True, False]
    ATTENTION_OPTIONS = [True, False]

    def __init__(self, config: NASConfig):
        self.config = config

    def random_gene(self) -> ArchitectureGene:
        """Случайный ген."""
        return ArchitectureGene(
            cell_type=random.choice(self.CELL_TYPES),
            num_filters=random.choice(self.FILTER_SIZES),
            kernel_size=random.choice(self.KERNEL_SIZES),
            num_repeats=random.randint(1, 3),
            use_se=random.choice(self.SE_OPTIONS),
            use_attention=random.choice(self.ATTENTION_OPTIONS),
            activation=random.choice(self.ACTIVATIONS),
            normalization=random.choice(self.NORMALIZATIONS),
            dropout_rate=random.uniform(0.0, 0.5),
            residual=random.choice(self.RESIDUAL_OPTIONS),
            depthwise=random.choice(self.DEPTHWISE_OPTIONS),
            dilated=random.choice(self.DILATED_OPTIONS),
        )

    def random_architecture(self) -> Architecture:
        """Случайная архитектура."""
        num_genes = random.randint(
            self.config.num_cells // 2,
            self.config.num_cells * 2,
        )
        genes = [self.random_gene() for _ in range(num_genes)]
        arch_id = f"arch_{random.randint(0, 999999):06d}"
        return Architecture(genes=genes, architecture_id=arch_id)

    def mutate_gene(self, gene: ArchitectureGene) -> ArchitectureGene:
        """Мутация одного гена."""
        mutated = ArchitectureGene(**gene.to_dict())
        mutation_field = random.choice(list(mutated.to_dict().keys()))

        if mutation_field == "cell_type":
            mutated.cell_type = random.choice(self.CELL_TYPES)
        elif mutation_field == "num_filters":
            mutated.num_filters = random.choice(self.FILTER_SIZES)
        elif mutation_field == "kernel_size":
            mutated.kernel_size = random.choice(self.KERNEL_SIZES)
        elif mutation_field == "num_repeats":
            mutated.num_repeats = random.randint(1, 3)
        elif mutation_field == "use_se":
            mutated.use_se = not mutated.use_se
        elif mutation_field == "use_attention":
            mutated.use_attention = not mutated.use_attention
        elif mutation_field == "activation":
            mutated.activation = random.choice(self.ACTIVATIONS)
        elif mutation_field == "normalization":
            mutated.normalization = random.choice(self.NORMALIZATIONS)
        elif mutation_field == "dropout_rate":
            mutated.dropout_rate = random.uniform(0.0, 0.5)
        elif mutation_field == "residual":
            mutated.residual = not mutated.residual
        elif mutation_field == "depthwise":
            mutated.depthwise = not mutated.depthwise
        elif mutation_field == "dilated":
            mutated.dilated = not mutated.dilated

        return mutated

    def crossover(self, parent1: Architecture, parent2: Architecture) -> Architecture:
        """Скрещивание двух архитектур."""
        max_len = max(len(parent1.genes), len(parent2.genes))
        child_genes = []

        for i in range(max_len):
            if random.random() < 0.5:
                if i < len(parent1.genes):
                    child_genes.append(deepcopy(parent1.genes[i]))
                elif i < len(parent2.genes):
                    child_genes.append(deepcopy(parent2.genes[i]))
            else:
                if i < len(parent2.genes):
                    child_genes.append(deepcopy(parent2.genes[i]))
                elif i < len(parent1.genes):
                    child_genes.append(deepcopy(parent1.genes[i]))

        return Architecture(
            genes=child_genes,
            architecture_id=f"arch_{random.randint(0, 999999):06d}",
        )


class WeightSharingEstimator:
    """Оценка производительности с разделением весов."""

    def __init__(self, config: NASConfig):
        self.config = config
        self.shared_weights: Dict[str, Any] = {}
        self.performance_cache: Dict[str, float] = {}

    def estimate_parameters(self, architecture: Architecture) -> int:
        """Оценка числа параметров."""
        total_params = 0
        in_channels = 3

        for gene in architecture.genes:
            if gene.cell_type in ("encoder", "decoder", "bottleneck"):
                if gene.depthwise:
                    params = gene.kernel_size**2 * in_channels + gene.num_filters
                else:
                    params = gene.kernel_size**2 * in_channels * gene.num_filters

                if gene.use_se:
                    params += 2 * gene.num_filters * gene.num_filters // 16

                params *= gene.num_repeats
                total_params += params
                in_channels = gene.num_filters

        return int(total_params)

    def estimate_flops(self, architecture: Architecture, input_shape: Tuple[int, ...] = (256, 256, 3)) -> float:
        """Оценка FLOPs."""
        total_flops = 0.0
        in_channels = input_shape[-1]
        spatial_size = input_shape[0] * input_shape[1]

        for gene in architecture.genes:
            if gene.cell_type in ("encoder", "decoder", "bottleneck"):
                if gene.depthwise:
                    flops = gene.kernel_size**2 * spatial_size * in_channels + spatial_size * gene.num_filters
                else:
                    flops = gene.kernel_size**2 * spatial_size * in_channels * gene.num_filters

                if gene.use_se:
                    flops += 2 * spatial_size * gene.num_filters**2 // 16

                flops *= gene.num_repeats
                total_flops += flops

                if gene.cell_type == "encoder":
                    spatial_size = spatial_size // 4
                elif gene.cell_type == "decoder":
                    spatial_size = spatial_size * 4

                in_channels = gene.num_filters

        return total_flops

    def estimate_inference_time(
        self, architecture: Architecture, input_shape: Tuple[int, ...] = (256, 256, 3)
    ) -> float:
        """Оценка времени инференса (мс)."""
        flops = self.estimate_flops(architecture, input_shape)
        base_throughput = 1e9
        estimated_time = (flops / base_throughput) * 1000
        return estimated_time

    def compute_fitness(self, architecture: Architecture, input_shape: Tuple[int, ...] = (256, 256, 3)) -> float:
        """Вычисление fitness архитектуры."""
        arch_key = architecture.architecture_id
        if arch_key in self.performance_cache:
            return self.performance_cache[arch_key]

        num_params = self.estimate_parameters(architecture)
        flops = self.estimate_flops(architecture, input_shape)
        inference_time = self.estimate_inference_time(architecture, input_shape)

        param_score = max(0, 1.0 - num_params / self.config.target_params)
        flops_score = max(0, 1.0 - flops / self.config.target_flops)
        time_score = max(0, 1.0 - inference_time / 100.0)

        complexity_penalty = 0.0
        for gene in architecture.genes:
            if gene.use_se:
                complexity_penalty += 0.02
            if gene.use_attention:
                complexity_penalty += 0.03
            complexity_penalty += gene.dropout_rate * 0.05

        fitness = 0.4 * param_score + 0.3 * flops_score + 0.3 * time_score - complexity_penalty

        architecture.num_params = num_params
        architecture.flops = flops
        architecture.inference_time = inference_time
        architecture.fitness = max(0.0, min(1.0, fitness))

        self.performance_cache[arch_key] = architecture.fitness
        return architecture.fitness


class EvolutionarySearch:
    """Эволюционный поиск архитектур."""

    def __init__(self, config: NASConfig):
        self.config = config
        self.search_space = SearchSpace(config)
        self.estimator = WeightSharingEstimator(config)
        self.population: List[Architecture] = []
        self.best_architectures: List[Architecture] = []
        self.generation = 0
        self.search_history: List[Dict[str, Any]] = []

    def initialize_population(self) -> None:
        """Инициализация популяции."""
        self.population = []
        for _ in range(self.config.population_size):
            arch = self.search_space.random_architecture()
            self.estimator.compute_fitness(arch)
            self.population.append(arch)

        self.population.sort(key=lambda a: a.fitness, reverse=True)
        logger.info(f"Популяция инициализирована: лучший fitness = {self.population[0].fitness:.4f}")

    def tournament_select(self) -> Architecture:
        """Турнирная селекция."""
        candidates = random.sample(
            self.population,
            min(self.config.tournament_size, len(self.population)),
        )
        return max(candidates, key=lambda a: a.fitness)

    def evolve_generation(self) -> Dict[str, Any]:
        """Эволюция одного поколения."""
        self.generation += 1
        new_population = []

        elite_count = max(1, self.config.population_size // 5)
        new_population.extend(deepcopy(self.population[:elite_count]))

        while len(new_population) < self.config.population_size:
            if random.random() < self.config.crossover_rate:
                parent1 = self.tournament_select()
                parent2 = self.tournament_select()
                child = self.search_space.crossover(parent1, parent2)
            else:
                child = deepcopy(self.tournament_select())

            if random.random() < self.config.mutation_rate:
                mutated_genes = [self.search_space.mutate_gene(g) for g in child.genes]
                child.genes = mutated_genes

            self.estimator.compute_fitness(child)
            new_population.append(child)

        new_population.sort(key=lambda a: a.fitness, reverse=True)
        self.population = new_population[: self.config.population_size]

        best = self.population[0]
        avg_fitness = np.mean([a.fitness for a in self.population])

        gen_stats = {
            "generation": self.generation,
            "best_fitness": best.fitness,
            "avg_fitness": float(avg_fitness),
            "best_params": best.num_params,
            "best_flops": best.flops,
            "population_size": len(self.population),
        }
        self.search_history.append(gen_stats)

        if not self.best_architectures or best.fitness > self.best_architectures[0].fitness:
            self.best_architectures = [deepcopy(best)]
        elif len(self.best_architectures) < 10:
            if best.fitness > min(a.fitness for a in self.best_architectures):
                self.best_architectures.append(deepcopy(best))
                self.best_architectures.sort(key=lambda a: a.fitness, reverse=True)
                self.best_architectures = self.best_architectures[:10]

        logger.info(f"Поколение {self.generation}: лучший={best.fitness:.4f}, средний={avg_fitness:.4f}")
        return gen_stats

    def search(self, num_generations: Optional[int] = None) -> Architecture:
        """Запуск полного поиска."""
        generations = num_generations or self.config.generations
        self.initialize_population()

        for gen in range(generations):
            self.evolve_generation()

        best = self.population[0]
        logger.info(f"Поиск завершён: лучшая fitness = {best.fitness:.4f}")
        return best

    def get_top_k(self, k: int = 5) -> List[Architecture]:
        """Топ-K архитектур."""
        return self.population[:k]

    def save_search_results(self, path: str) -> None:
        """Сохранение результатов поиска."""
        results = {
            "config": {
                "search_space": self.config.search_space,
                "population_size": self.config.population_size,
                "generations": self.config.generations,
            },
            "search_history": self.search_history,
            "top_architectures": [a.to_dict() for a in self.get_top_k(5)],
            "best_architectures": [a.to_dict() for a in self.best_architectures[:5]],
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Результаты поиска сохранены: {path}")


class NASManager:
    """Менеджер нейронного поиска архитектур."""

    def __init__(self, config: NASConfig):
        self.config = config
        self.search = EvolutionarySearch(config)
        self.search_space = SearchSpace(config)
        self.results: List[Architecture] = []

    def run_search(self, num_generations: Optional[int] = None) -> Architecture:
        """Запуск поиска."""
        best = self.search.search(num_generations)
        self.results = self.search.get_top_k(10)
        return best

    def build_model_from_architecture(self, architecture: Architecture):
        """Построение модели из архитектуры."""
        import tensorflow as tf

        inputs = tf.keras.Input(shape=(256, 256, 3))
        x = inputs

        encoders = []
        for gene in architecture.genes:
            if gene.cell_type == "encoder":
                for _ in range(gene.num_repeats):
                    if gene.depthwise:
                        x = tf.keras.layers.DepthwiseConv2D(gene.kernel_size, padding="same")(x)
                    else:
                        x = tf.keras.layers.Conv2D(gene.num_filters, gene.kernel_size, padding="same")(x)

                    if gene.normalization == "batch_norm":
                        x = tf.keras.layers.BatchNormalization()(x)
                    elif gene.normalization == "layer_norm":
                        x = tf.keras.layers.LayerNormalization()(x)

                    if gene.activation == "relu":
                        x = tf.keras.layers.ReLU()(x)
                    elif gene.activation == "leaky_relu":
                        x = tf.keras.layers.LeakyReLU()(x)
                    elif gene.activation == "swish":
                        x = tf.keras.layers.Activation("swish")(x)
                    elif gene.activation == "gelu":
                        x = tf.keras.layers.Activation("gelu")(x)

                encoders.append(x)
                x = tf.keras.layers.MaxPooling2D(2)(x)

            elif gene.cell_type == "bottleneck":
                for _ in range(gene.num_repeats):
                    if gene.depthwise:
                        x = tf.keras.layers.DepthwiseConv2D(
                            gene.kernel_size, padding="same", dilation_rate=2 if gene.dilated else 1
                        )(x)
                    else:
                        x = tf.keras.layers.Conv2D(
                            gene.num_filters,
                            gene.kernel_size,
                            padding="same",
                            dilation_rate=2 if gene.dilated else 1,
                        )(x)
                    x = tf.keras.layers.BatchNormalization()(x)
                    x = tf.keras.layers.ReLU()(x)

        for gene in reversed(architecture.genes):
            if gene.cell_type == "decoder" and encoders:
                skip = encoders.pop()
                x = tf.keras.layers.UpSampling2D(2)(x)
                x = tf.keras.layers.Concatenate()([x, skip])
                for _ in range(gene.num_repeats):
                    x = tf.keras.layers.Conv2D(gene.num_filters, gene.kernel_size, padding="same")(x)
                    x = tf.keras.layers.BatchNormalization()(x)
                    x = tf.keras.layers.ReLU()(x)

        outputs = tf.keras.layers.Conv2D(self.config.num_classes, 1, activation="sigmoid")(x)

        return tf.keras.Model(inputs=inputs, outputs=outputs)

    def export_results(self, output_dir: str) -> None:
        """Экспорт результатов поиска."""
        os.makedirs(output_dir, exist_ok=True)

        self.search.save_search_results(os.path.join(output_dir, "nas_results.json"))

        for i, arch in enumerate(self.results[:5]):
            arch_path = os.path.join(output_dir, f"architecture_{i}.json")
            with open(arch_path, "w") as f:
                json.dump(arch.to_dict(), f, indent=2)

        logger.info(f"Результаты экспортированы в {output_dir}")
