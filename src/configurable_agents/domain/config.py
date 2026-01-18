"""
Domain Configuration Models

Pure Python dataclasses representing the domain model.
These are framework-agnostic and contain no business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMConfig:
    """LLM configuration at any level (global/crew/agent/task)."""
    
    provider: str = "google"
    model: Optional[str] = None  # If None, uses environment MODEL variable
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    def merge_with(self, parent: Optional['LLMConfig']) -> 'LLMConfig':
        """
        Merge this config with a parent config.
        Child values override parent values.
        
        Args:
            parent: Parent LLM config to merge with
            
        Returns:
            New LLMConfig with merged values
        """
        if parent is None:
            return self
        
        return LLMConfig(
            provider=self.provider if self.provider != "google" else parent.provider,
            model=self.model or parent.model,
            temperature=self.temperature if self.temperature != 0.7 else parent.temperature,
            max_tokens=self.max_tokens or parent.max_tokens,
        )


@dataclass
class AgentConfig:
    """Agent configuration within a crew."""
    
    id: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    llm: Optional[LLMConfig] = None
    
    def __post_init__(self):
        """Validate agent configuration."""
        if not self.id:
            raise ValueError("Agent ID cannot be empty")
        if not self.role:
            raise ValueError(f"Agent '{self.id}' must have a role")
        if not self.goal:
            raise ValueError(f"Agent '{self.id}' must have a goal")


@dataclass
class TaskConfig:
    """Task configuration within a crew."""
    
    id: str
    description: str
    expected_output: str
    agent: str  # Reference to agent ID
    context: List[str] = field(default_factory=list)  # List of task IDs
    output_model: Optional[Dict[str, Any]] = None
    llm: Optional[LLMConfig] = None
    
    def __post_init__(self):
        """Validate task configuration."""
        if not self.id:
            raise ValueError("Task ID cannot be empty")
        if not self.description:
            raise ValueError(f"Task '{self.id}' must have a description")
        if not self.agent:
            raise ValueError(f"Task '{self.id}' must be assigned to an agent")


@dataclass
class ExecutionConfig:
    """Execution configuration for a crew."""
    
    type: str = "sequential"  # 'sequential' or 'hierarchical'
    tasks: List[str] = field(default_factory=list)  # Ordered list of task IDs
    manager_agent: Optional[str] = None  # For hierarchical execution
    manager_llm: Optional[LLMConfig] = None  # For hierarchical execution
    
    def __post_init__(self):
        """Validate execution configuration."""
        if self.type not in ["sequential", "hierarchical"]:
            raise ValueError(f"Execution type must be 'sequential' or 'hierarchical', got '{self.type}'")
        
        if self.type == "hierarchical" and not self.manager_llm:
            raise ValueError("Hierarchical execution requires manager_llm configuration")


@dataclass
class CrewConfig:
    """Crew configuration containing agents and tasks."""
    
    agents: List[AgentConfig] = field(default_factory=list)
    tasks: List[TaskConfig] = field(default_factory=list)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    llm: Optional[LLMConfig] = None
    
    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent by ID."""
        return next((a for a in self.agents if a.id == agent_id), None)
    
    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """Get task by ID."""
        return next((t for t in self.tasks if t.id == task_id), None)
    
    def get_agent_ids(self) -> List[str]:
        """Get all agent IDs."""
        return [a.id for a in self.agents]
    
    def get_task_ids(self) -> List[str]:
        """Get all task IDs."""
        return [t.id for t in self.tasks]


@dataclass
class StepConfig:
    """Flow step configuration."""
    
    id: str
    type: str = "crew"
    crew_ref: str = ""
    is_start: bool = False
    next_step: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    output_to_state: str = ""
    
    def __post_init__(self):
        """Validate step configuration."""
        if not self.id:
            raise ValueError("Step ID cannot be empty")
        if self.type not in ["crew"]:
            raise ValueError(f"Step type must be 'crew', got '{self.type}'")
        if self.type == "crew" and not self.crew_ref:
            raise ValueError(f"Step '{self.id}' of type 'crew' must have crew_ref")


@dataclass
class StateConfig:
    """State configuration for the flow."""
    
    common_vars: List[str] = field(default_factory=list)
    
    @property
    def has_execution_id(self) -> bool:
        """Check if execution_id is tracked."""
        return "execution_id" in self.common_vars
    
    @property
    def has_current_step(self) -> bool:
        """Check if current_step is tracked."""
        return "current_step" in self.common_vars


@dataclass
class FlowMetadata:
    """Flow metadata."""
    
    name: str
    description: str = ""


@dataclass
class FlowConfig:
    """Complete flow configuration."""
    
    flow: FlowMetadata
    steps: List[StepConfig]
    crews: Dict[str, CrewConfig]
    defaults: LLMConfig = field(default_factory=LLMConfig)
    state: Optional[StateConfig] = None
    
    def get_step(self, step_id: str) -> Optional[StepConfig]:
        """Get step by ID."""
        return next((s for s in self.steps if s.id == step_id), None)
    
    def get_crew(self, crew_name: str) -> Optional[CrewConfig]:
        """Get crew by name."""
        return self.crews.get(crew_name)
    
    def get_start_step(self) -> Optional[StepConfig]:
        """Get the starting step."""
        return next((s for s in self.steps if s.is_start), None)
    
    def get_step_ids(self) -> List[str]:
        """Get all step IDs."""
        return [s.id for s in self.steps]
    
    def get_crew_names(self) -> List[str]:
        """Get all crew names."""
        return list(self.crews.keys())
    
    def count_agents(self) -> int:
        """Count total agents across all crews."""
        return sum(len(crew.agents) for crew in self.crews.values())
    
    def count_tasks(self) -> int:
        """Count total tasks across all crews."""
        return sum(len(crew.tasks) for crew in self.crews.values())


# Type aliases for clarity
ConfigDict = Dict[str, Any]
YAMLDict = Dict[str, Any]