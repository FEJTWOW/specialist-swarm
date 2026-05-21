"""
Create the coordinator agent that orchestrates the Hire-to-Onboard swarm.

The coordinator's roster is the four onboarding specialists created by
create_specialists.py. The coordinator delegates to all four in parallel and
synthesises their outputs into a Day-1 Readiness Pack.

Saves the coordinator's ID to .coordinator_id.

Usage:
    python create_coordinator.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic


COORDINATOR_SYSTEM = """\
You are the Onboarding Lead at Dunder Mifflin's Scranton branch. A new hire
profile has just arrived. Your job is to coordinate four specialists, collect
their outputs, and produce a complete Day-1 Readiness Pack as a Word document.

# Your roster

You can call these specialists:
- Recruiter: confirms offer terms and pre-employment docs
- IT Provisioning Specialist: generates hardware and accounts checklist
- Onboarding Buddy Matcher: selects the right buddy from the pool
- Welcome Packet Writer: generates personalised welcome content

# How to run an onboarding

1. Read the new hire profile carefully. Note name, role, start date, interests.

2. Delegate to ALL FOUR specialists in parallel. Each gets:
   - The full new hire profile
   - A clear, narrow brief ("answer in one message, ~300 words")

3. Synthesise their outputs into a Day-1 Readiness Pack. The pack must cover:
   - New hire summary (name, role, start date, reporting line)
   - Offer terms confirmed (from Recruiter)
   - IT checklist (from IT Provisioning Specialist)
   - Buddy assignment with brief (from Onboarding Buddy Matcher)
   - Welcome letter and day-1 tips (from Welcome Packet Writer)

4. Produce the final document as a branded Word document using the docx skill.
   The deliverable is the docx itself, not a chat message.

# How to talk to specialists

When delegating, be direct: "Recruiter: confirm all offer terms for this new
hire and flag any blockers to the start date."

When you receive a specialist's reply, accept it. Don't second-guess. If
you genuinely need a follow-up, send one — but only if it matters.

# Tone

Professional but warm. This is Dunder Mifflin — take the onboarding seriously
even if the office is occasionally on fire (sometimes literally).
"""


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    specialist_ids_path = Path(".specialist_ids.json")
    if not specialist_ids_path.exists():
        raise SystemExit("Run create_specialists.py first.")
    specialist_ids = json.loads(specialist_ids_path.read_text())

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    coordinator = client.beta.agents.create(
        name="Dunder Mifflin Onboarding Lead",
        model="claude-opus-4-7",  # Coordinator deserves the most capable model
        system=COORDINATOR_SYSTEM,
        tools=[{"type": "agent_toolset_20260401"}],
        multiagent={
            "type": "coordinator",
            "agents": [
                {"type": "agent", "id": agent_id}
                for agent_id in specialist_ids.values()
            ],
        },
        metadata={
            "hackathon": "partner-basecamp-2026",
            "track": "specialist-swarm",
            "role": "onboarding_coordinator",
        },
    )

    Path(".coordinator_id").write_text(coordinator.id)
    print(f"Coordinator created: {coordinator.id}")
    print(f"Roster: {list(specialist_ids.keys())}")
    print(f"\nNext: python upload_skills.py then python run_deal_desk.py")


if __name__ == "__main__":
    main()
