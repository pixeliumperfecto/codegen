from codegen.extensions.swebench.utils import SweBenchExample
from codegen.extensions.swebench.harness import run_agent_on_entry
import modal

image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .pip_install("fastapi[standard]")
    .copy_local_dir("../../../", "/root/codegen", ignore=[".venv", "**/.venv", "tests", "**/tests"])
    .run_commands("pip install -e /root/codegen")
)

app = modal.App(name="swebench-agent-run", image=image, secrets=[modal.Secret.from_dotenv()])


@app.function(timeout=5 * 60)
async def run_agent_modal(entry: SweBenchExample):
    """Modal function to process a single example from the SWE-bench dataset."""
    return run_agent_on_entry(entry)
