from langgraph.graph import StateGraph, START, END
from app.schemas.state import AgentState
from app.nodes.scan import scan_outfit
from app.nodes.critique import critique_outfit
from app.nodes.retrieve import retrieve_products

# =========================================================================================
# PHASE 4 - LANGGRAPH WORKFLOW (Updated)
# Workflow: START -> scan_outfit -> critique_outfit -> retrieve_products -> END
# =========================================================================================

workflow = StateGraph(AgentState)

# 1. Add nodes
workflow.add_node("scan", scan_outfit)
workflow.add_node("critique", critique_outfit)
workflow.add_node("retrieve", retrieve_products)

# 2. Define edges
workflow.add_edge(START, "scan")
workflow.add_edge("scan", "critique")
workflow.add_edge("critique", "retrieve")
workflow.add_edge("retrieve", END)

# 3. Compile the graph
app = workflow.compile()
