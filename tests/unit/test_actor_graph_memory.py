from __future__ import annotations


def test_graph_traversal_policy_bounds_customer_query_walks() -> None:
    from packages.core.actor_runtime import GraphTraversalPolicy

    policy = GraphTraversalPolicy(max_depth=3, max_nodes=250, max_edges=750)
    budget = policy.bound_request(requested_depth=10, requested_nodes=1000, requested_edges=5000)

    assert budget.depth == 3
    assert budget.nodes == 250
    assert budget.edges == 750
    assert budget.truncated is True
    assert budget.cycle_strategy == "collapse_scc"


def test_graph_traversal_policy_records_stop_on_cycle_mode() -> None:
    from packages.core.actor_runtime import GraphTraversalPolicy

    policy = GraphTraversalPolicy(collapse_strongly_connected_components=False)
    budget = policy.bound_request(requested_depth=2, requested_nodes=10, requested_edges=20)

    assert budget.depth == 2
    assert budget.nodes == 10
    assert budget.edges == 20
    assert budget.truncated is False
    assert budget.cycle_strategy == "stop_on_cycle"
