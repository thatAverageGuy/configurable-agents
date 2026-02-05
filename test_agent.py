#!/usr/bin/env python
"""
Test Agent for Orchestrator E2E Testing

A simple FastAPI agent that mimics a real workflow agent.
Can be used to test the orchestrator's manual registration,
health checking, schema fetching, and workflow execution features.

Usage:
    python test_agent.py

The agent will start on http://127.0.0.1:8002

Then register it in the orchestrator:
    Agent ID: test-agent
    Agent Name: Test Agent
    Agent URL: http://localhost:8002
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, Optional
import uvicorn

# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="Test Workflow Agent",
    description="Simple agent for orchestrator E2E testing",
    version="1.0.0"
)

# ============================================
# Request/Response Models
# ============================================

class WorkflowInput(BaseModel):
    """Input schema for the test workflow."""
    topic: str = Field(
        ...,
        description="Topic to research or process",
        example="AI and machine learning"
    )
    tone: str = Field(
        default="neutral",
        description="Tone of the output (neutral, formal, casual)",
        example="neutral"
    )
    length: Optional[str] = Field(
        default="short",
        description="Output length (short, medium, long)",
        example="short"
    )


class RunResponse(BaseModel):
    """Response from workflow execution."""
    status: str
    execution_time_ms: Optional[int] = None
    outputs: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None
    message: Optional[str] = None


class SchemaResponse(BaseModel):
    """Workflow schema response."""
    workflow: str
    inputs: Dict[str, Any]
    outputs: list[str]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str
    agent_id: str


# ============================================
# Routes
# ============================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "agent": "Test Workflow Agent",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "schema": "GET /schema",
            "run": "POST /run",
            "docs": "GET /docs"
        },
        "capabilities": [
            "text_generation",
            "research",
            "summarization"
        ]
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns agent liveness status. Called by orchestrator during
    registration and periodic health checks.
    """
    return HealthResponse(
        status="alive",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        agent_id="test-agent"
    )


@app.get("/schema", response_model=SchemaResponse, tags=["Schema"])
async def get_schema():
    """
    Get workflow schema.

    Returns the input/output schema for this agent's workflow.
    Called by orchestrator when user clicks [Execute] button.
    """
    return SchemaResponse(
        workflow="test-workflow",
        inputs={
            "topic": {
                "type": "str",
                "description": "Topic to research or process",
                "required": True
            },
            "tone": {
                "type": "str",
                "description": "Tone of the output (neutral, formal, casual)",
                "required": False
            },
            "length": {
                "type": "str",
                "description": "Output length (short, medium, long)",
                "required": False
            }
        },
        outputs=["result", "summary", "word_count"]
    )


@app.post("/run", response_model=RunResponse, tags=["Execution"])
async def run_workflow(inputs: WorkflowInput):
    """
    Execute the workflow.

    Processes the input and returns simulated results.
    Called by orchestrator when user submits the execute form.

    Args:
        inputs: Validated workflow inputs

    Returns:
        Execution results with outputs and metadata
    """
    import time
    import random

    start_time = time.time()

    # Simulate processing time (100-500ms)
    await asyncio.sleep(0.1 + (random.random() * 0.4))

    execution_time_ms = int((time.time() - start_time) * 1000)

    # Simulate workflow logic
    topic = inputs.topic
    tone = inputs.tone
    length = inputs.length

    # Generate mock results
    result_text = f"[Test Agent] Processed topic: '{topic}'"

    if tone == "formal":
        result_text += " (Formal tone)"
    elif tone == "casual":
        result_text += " (Casual tone)"

    word_count = len(result_text.split())

    outputs = {
        "result": result_text,
        "summary": f"Generated summary for: {topic}",
        "word_count": word_count,
        "tone_used": tone,
        "length_setting": length
    }

    # Simulate token usage and cost
    total_tokens = word_count + 50  # Base tokens + output tokens
    total_cost_usd = round(total_tokens * 0.00002, 6)

    return RunResponse(
        status="success",
        execution_time_ms=execution_time_ms,
        outputs=outputs,
        message=f"Workflow completed in {execution_time_ms}ms"
    )


@app.get("/docs", include_in_schema=False)
async def docs():
    """Redirect to ReDoc documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs#")


# ============================================
# Startup Event
# ============================================

@app.on_event("startup")
async def startup_event():
    """Log startup message."""
    print("=" * 60)
    print("TEST AGENT STARTED")
    print("=" * 60)
    print("Agent ID: test-agent")
    print("Agent Name: Test Workflow Agent")
    print("URL: http://127.0.0.1:8002")
    print("")
    print("Endpoints:")
    print("  GET  /health  - Health check")
    print("  GET  /schema  - Workflow schema")
    print("  POST /run    - Execute workflow")
    print("  GET  /docs    - API documentation")
    print("")
    print("Ready for orchestrator registration!")
    print("=" * 60)


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import asyncio

    print("Starting Test Agent...")
    print("This agent will simulate a workflow agent for orchestrator testing.")
    print("")
    print("To stop: Press Ctrl+C")
    print("")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
        log_level="info"
    )
