"""
API routes for agents — status, trigger, history.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/agents", tags=["Agents"])


def _get_all_agents():
    from agents import ALL_AGENTS
    return ALL_AGENTS


@router.get("/")
async def list_agents():
    """Get status of all agents."""
    agents = _get_all_agents()
    return [agent.get_status() for agent in agents.values()]


@router.get("/{agent_name}")
async def get_agent(agent_name: str):
    """Get status of a specific agent."""
    agents = _get_all_agents()
    agent = agents.get(agent_name)
    if not agent:
        return {"error": f"Agent '{agent_name}' not found"}
    return agent.get_status()


@router.post("/{agent_name}/run")
async def run_agent(agent_name: str, story_id: str = None, script_id: str = None,
                    reel_id: str = None, action: str = None):
    """Trigger an agent run."""
    agents = _get_all_agents()
    agent = agents.get(agent_name)
    if not agent:
        return {"error": f"Agent '{agent_name}' not found"}

    kwargs = {}
    if story_id:
        kwargs["story_id"] = story_id
    if script_id:
        kwargs["script_id"] = script_id
    if reel_id:
        kwargs["reel_id"] = reel_id
    if action:
        kwargs["action"] = action

    result = await agent.run(**kwargs)
    return result


@router.get("/{agent_name}/history")
async def agent_history(agent_name: str, limit: int = 10):
    """Get run history for an agent."""
    agents = _get_all_agents()
    agent = agents.get(agent_name)
    if not agent:
        return {"error": f"Agent '{agent_name}' not found"}
    return agent.get_history(limit)


@router.post("/pipeline/run")
async def run_pipeline():
    """Run the complete pipeline: scrape → rank → write → visual → avatar."""
    from agents import PIPELINE_ORDER
    agents = _get_all_agents()
    results = {}

    for name in PIPELINE_ORDER:
        agent = agents.get(name)
        if agent:
            result = await agent.run()
            results[name] = result
            if result.get("status") == "failed":
                break

    return {"pipeline": results}
