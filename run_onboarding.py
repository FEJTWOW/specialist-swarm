"""
Run the Hire-to-Onboard swarm against a new hire profile.

Inlines the new-hire-profile.md into the user message. Streams events as they
come in so you can watch the parallel thread fan-out — this is the demo.

Saves the final transcript and any produced files to outputs/.

Usage:
    python run_onboarding.py
"""

import os
from pathlib import Path

from anthropic import Anthropic


NEW_HIRE_PATH = Path("synthetic-data/new-hire-profile.md")
OUTPUT_DIR = Path("outputs")


def load_inputs_as_context() -> str:
    if not NEW_HIRE_PATH.exists():
        raise SystemExit(f"Missing {NEW_HIRE_PATH} — create it first.")
    print(f"  including {NEW_HIRE_PATH.name}")
    return f"=====  DOCUMENT: {NEW_HIRE_PATH.name}  =====\n{NEW_HIRE_PATH.read_text()}"


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    if not Path(".coordinator_id").exists() or not Path(".environment_id").exists():
        raise SystemExit(
            "Missing .coordinator_id or .environment_id. Run "
            "create_specialists.py, upload_skills.py, then create_coordinator.py first."
        )

    coordinator_id = Path(".coordinator_id").read_text().strip()
    environment_id = Path(".environment_id").read_text().strip()

    client = Anthropic()

    print("Loading new hire profile...")
    context = load_inputs_as_context()

    print(f"\nStarting session against coordinator {coordinator_id}...")
    session = client.beta.sessions.create(
        agent=coordinator_id,
        environment_id=environment_id,
        title="Onboarding — Alex Rivera (Dunder Mifflin)",
    )
    Path(".last_session_id").write_text(session.id)

    user_message = (
        "A new hire profile has just arrived. Please run the standard onboarding process:\n"
        "1. Read the new hire profile yourself.\n"
        "2. Delegate to all four specialists in parallel.\n"
        "3. Synthesise their replies.\n"
        "4. Produce the final Day-1 Readiness Pack as a branded Word document "
        "if you have access to a docx skill; otherwise output the pack "
        "as a structured markdown document.\n\n"
        "Specialists have their own skills attached for their respective "
        "domains. Move fast — the new hire starts on June 2nd.\n\n"
        f"{context}"
    )

    # Stream the events — this is the demo. Watch for parallel thread spawns.
    print("\n=== EVENT STREAM (this is the demo) ===\n")
    final_text_parts: list[str] = []

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_message}],
                }
            ],
        )
        for event in stream:
            t = event.type
            if t == "session.thread_created":
                print(f"  [thread spawned]   {event.agent_name}", flush=True)
            elif t == "session.thread_status_running":
                name = getattr(event, "agent_name", "?")
                print(f"  [thread running]   {name}", flush=True)
            elif t == "agent.thread_message_received":
                print(f"  [reply ←]          {event.from_agent_name}", flush=True)
            elif t == "agent.thread_message_sent":
                print(f"  [delegate →]       {event.to_agent_name}", flush=True)
            elif t == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        final_text_parts.append(block.text)
                        print(block.text, end="", flush=True)
            elif t == "agent.tool_use":
                print(f"\n  [tool: {getattr(event, 'name', '?')}]", flush=True)
            elif t == "session.status_idle":
                print("\n\n[swarm finished]")
                break

    OUTPUT_DIR.mkdir(exist_ok=True)
    transcript_path = OUTPUT_DIR / "onboarding-transcript.txt"
    transcript_path.write_text("".join(final_text_parts))
    print(f"\nCoordinator transcript saved to {transcript_path}")

    # Pull every file the agents produced in the container
    print("\nDownloading deliverables from the session container...")
    files = client.beta.files.list(
        scope_id=session.id,
        betas=["managed-agents-2026-04-01"],
    )
    file_count = 0
    for f in files.data:
        out_path = OUTPUT_DIR / f.filename
        print(f"  {f.filename}  ->  {out_path}")
        content = client.beta.files.download(f.id)
        content.write_to_file(str(out_path))
        file_count += 1

    if file_count == 0:
        print("  (no files found — agents may have produced text-only output)")
    else:
        print(f"\nDownloaded {file_count} file(s) to {OUTPUT_DIR}/")

    print(f"\nView the full session (including all sub-agent threads) at:")
    print(f"  https://platform.claude.com/sessions/{session.id}")


if __name__ == "__main__":
    main()
