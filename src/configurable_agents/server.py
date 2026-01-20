from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from configurable_agents.main import run_flow_from_file

app = FastAPI(title="Agent Service")

# Config path injected via Docker env vars
CONFIG_PATH = os.getenv("FLOW_CONFIG", "flow.yaml")

class TriggerRequest(BaseModel):
    inputs: Dict[str, Any] = {}

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "active", "config": CONFIG_PATH}

@app.post("/kickoff")
async def kickoff(request: TriggerRequest):
    """Trigger the agent flow."""
    try:
        # Re-use existing logic to run the flow
        print(f"Triggering flow with inputs: {request.inputs}")
        result = run_flow_from_file(CONFIG_PATH, request.inputs)
        
        # Handle CrewAI output types safely
        final_output = result.raw if hasattr(result, 'raw') else str(result)
        
        return {
            "status": "success", 
            "output": final_output,
            "full_state": result if isinstance(result, dict) else None
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))