"""
Base agent class for all Talentsia pipeline agents.
Provides logging, status tracking, error handling, and run history.
"""

import logging
import time
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class BaseAgent:
    """Base class for all pipeline agents."""

    name: str = "base"
    description: str = ""

    def __init__(self):
        self.status = AgentStatus.IDLE
        self.last_run = None
        self.last_error = None
        self.last_duration = None
        self.run_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.run_history = []
        self.logger = logging.getLogger(f"agent.{self.name}")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    async def run(self, **kwargs) -> dict:
        """Execute the agent's main task with timing and error tracking."""
        self.status = AgentStatus.RUNNING
        self.last_run = datetime.utcnow()
        self.run_count += 1
        start_time = time.time()
        self.logger.info(f"🚀 Agent {self.name} starting (run #{self.run_count})")

        try:
            result = await self.execute(**kwargs)
            self.status = AgentStatus.SUCCESS
            self.success_count += 1
            self.last_error = None
            self.last_duration = round(time.time() - start_time, 2)

            run_record = {
                "run_number": self.run_count,
                "status": "success",
                "duration": self.last_duration,
                "timestamp": self.last_run.isoformat(),
            }
            self.run_history.append(run_record)
            # Keep only last 50 runs
            self.run_history = self.run_history[-50:]

            self.logger.info(
                f"✅ Agent {self.name} completed in {self.last_duration}s"
            )
            return {"status": "success", "agent": self.name, "result": result}

        except Exception as e:
            self.status = AgentStatus.FAILED
            self.fail_count += 1
            self.last_error = str(e)
            self.last_duration = round(time.time() - start_time, 2)

            run_record = {
                "run_number": self.run_count,
                "status": "failed",
                "error": str(e),
                "duration": self.last_duration,
                "timestamp": self.last_run.isoformat(),
            }
            self.run_history.append(run_record)
            self.run_history = self.run_history[-50:]

            self.logger.error(f"❌ Agent {self.name} failed after {self.last_duration}s: {e}")
            return {"status": "failed", "agent": self.name, "error": str(e)}

    async def execute(self, **kwargs) -> dict:
        """Override this in subclasses with the agent's core logic."""
        raise NotImplementedError

    def get_status(self) -> dict:
        """Return the agent's current status with full metrics."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_error": self.last_error,
            "last_duration": self.last_duration,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "success_rate": (
                round(self.success_count / self.run_count * 100, 1)
                if self.run_count > 0
                else 0
            ),
        }

    def get_history(self, limit: int = 10) -> list[dict]:
        """Return recent run history."""
        return self.run_history[-limit:]
