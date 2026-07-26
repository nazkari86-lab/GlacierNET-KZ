"""Causal cascade graph with non-probabilistic evidence-strength screening."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import BasinState, StateVariable


@dataclass(frozen=True)
class CascadeNode:
    node_id: str
    node_type: str
    state_variables: tuple[StateVariable, ...] = ()


@dataclass(frozen=True)
class CascadeEdge:
    source: str
    target: str
    mechanism: str
    required_variables: tuple[StateVariable, ...]
    evidence_sources: tuple[str, ...] = ()


@dataclass
class CascadeGraph:
    basin_id: str
    nodes: dict[str, CascadeNode] = field(default_factory=dict)
    edges: list[CascadeEdge] = field(default_factory=list)

    def add_node(self, node: CascadeNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"duplicate cascade node: {node.node_id}")
        self.nodes[node.node_id] = node

    def add_edge(self, edge: CascadeEdge) -> None:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError("cascade edge endpoints must exist")
        if edge.source == edge.target:
            raise ValueError("self-loop is not allowed")
        self.edges.append(edge)
        try:
            self._validate_acyclic()
        except ValueError:
            self.edges.pop()
            raise

    def _validate_acyclic(self) -> None:
        adjacency = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            adjacency[edge.source].append(edge.target)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("cascade graph must be acyclic")
            if node_id in visited:
                return
            visiting.add(node_id)
            for target in adjacency[node_id]:
                visit(target)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in self.nodes:
            visit(node_id)

    def paths(self, source: str, target: str) -> list[list[CascadeEdge]]:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("source and target must exist")
        adjacency: dict[str, list[CascadeEdge]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            adjacency[edge.source].append(edge)
        output: list[list[CascadeEdge]] = []

        def walk(node_id: str, path: list[CascadeEdge]) -> None:
            if node_id == target:
                output.append(path)
                return
            for edge in adjacency[node_id]:
                walk(edge.target, [*path, edge])

        walk(source, [])
        return output

    def screen_path(self, state: BasinState, path: list[CascadeEdge]) -> dict[str, Any]:
        required = {variable for edge in path for variable in edge.required_variables}
        observed = required & set(state.estimates)
        coverage = len(observed) / len(required) if required else 1.0
        relative_uncertainties = []
        for variable in observed:
            estimate = state.estimates[variable]
            scale = max(abs(estimate.mean), estimate.std, 1e-9)
            relative_uncertainties.append(min(1.0, estimate.std / scale))
        uncertainty_penalty = (
            sum(relative_uncertainties) / len(relative_uncertainties) if relative_uncertainties else 1.0
        )
        strength = max(0.0, min(1.0, coverage * (1 - uncertainty_penalty)))
        return {
            "mechanisms": [edge.mechanism for edge in path],
            "evidence_strength": strength,
            "evidence_scale": "screening_0_to_1_not_event_probability",
            "observed_variables": sorted(variable.value for variable in observed),
            "missing_variables": sorted(variable.value for variable in required - observed),
            "probability_interval": None,
            "probability_status": (
                "calibration_required" if not state.probability_calibrated else "calibrated model not implemented in v1"
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "basin_id": self.basin_id,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "state_variables": [variable.value for variable in node.state_variables],
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "from": edge.source,
                    "to": edge.target,
                    "mechanism": edge.mechanism,
                    "required_variables": [variable.value for variable in edge.required_variables],
                    "evidence_sources": list(edge.evidence_sources),
                }
                for edge in self.edges
            ],
        }


def default_glacial_lake_cascade(basin_id: str) -> CascadeGraph:
    graph = CascadeGraph(basin_id)
    for node in (
        CascadeNode(
            "parent_glacier",
            "glacier",
            (StateVariable.GLACIER_AREA, StateVariable.GLACIER_VELOCITY),
        ),
        CascadeNode(
            "glacial_lake",
            "glacial_lake",
            (StateVariable.LAKE_AREA, StateVariable.WATER_LEVEL, StateVariable.FREEBOARD),
        ),
        CascadeNode("unstable_slope", "slope", (StateVariable.SLOPE_DEFORMATION,)),
        CascadeNode(
            "moraine_dam",
            "dam_outlet",
            (StateVariable.DAM_STABILITY, StateVariable.OUTLET_CAPACITY),
        ),
        CascadeNode("downstream_channel", "channel", (StateVariable.CHANNEL_CAPACITY,)),
        CascadeNode("exposed_assets", "exposure", (StateVariable.EXPOSURE,)),
    ):
        graph.add_node(node)
    for edge in (
        CascadeEdge(
            "parent_glacier",
            "glacial_lake",
            "ice_mass_movement_or_melt_input",
            (StateVariable.GLACIER_VELOCITY, StateVariable.LAKE_AREA),
            ("ITS_LIVE", "Sentinel-2"),
        ),
        CascadeEdge(
            "unstable_slope",
            "glacial_lake",
            "mass_movement_into_lake",
            (StateVariable.SLOPE_DEFORMATION, StateVariable.LAKE_AREA),
            ("Sentinel-1 InSAR", "DEM"),
        ),
        CascadeEdge(
            "glacial_lake",
            "moraine_dam",
            "wave_or_overflow_loading",
            (StateVariable.WATER_LEVEL, StateVariable.FREEBOARD, StateVariable.DAM_STABILITY),
            ("SWOT", "ICESat-2", "field freeboard"),
        ),
        CascadeEdge(
            "moraine_dam",
            "downstream_channel",
            "breach_or_overtopping_release",
            (
                StateVariable.DAM_STABILITY,
                StateVariable.OUTLET_CAPACITY,
                StateVariable.CHANNEL_CAPACITY,
            ),
            ("DEM", "field outlet survey"),
        ),
        CascadeEdge(
            "downstream_channel",
            "exposed_assets",
            "runout_intersection",
            (StateVariable.CHANNEL_CAPACITY, StateVariable.EXPOSURE),
            ("DEM", "OpenStreetMap"),
        ),
    ):
        graph.add_edge(edge)
    return graph
