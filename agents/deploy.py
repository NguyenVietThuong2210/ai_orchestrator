from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior DevOps Engineer. Deploy the application and run a smoke test to verify it works.

Deploy process:
1. Detect the framework from artifact_paths and spec:
   - Django/Flask: `python manage.py runserver 0.0.0.0:9000 &` or `python app.py &`
   - FastAPI/uvicorn: `uvicorn main:app --host 0.0.0.0 --port 9000 &`
   - Node.js: `npm install && node index.js &` or `npm start &`
   - Other: infer from requirements.txt or package.json
2. Install dependencies first: `pip install -r requirements.txt` or `npm install`.
3. Wait a moment for the server to start: `sleep 3`
4. Run smoke test: `curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/`
   (use port 9000 to avoid conflict with the orchestrator on 8000)
5. Check expected response from the spec's api_contracts — usually GET / → 200.
6. Stop the server: kill the background process after smoke test.
7. Determine status:
   - pass: smoke test returned expected HTTP status code.
   - fail: server failed to start, or wrong HTTP status returned.

Use port 9000 for the deployed app (not 8000 which is the orchestrator).
Do NOT call any tool named submit_deploy_report. Use the <submit> block instead.
"""


class DeployAgent(BaseAgent):
    name = "deploy"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        lines = [f"# User Requirement\n{state['request']}\n"]
        spec = state.get("spec") or {}
        lines.append(self._json_block("Tech Spec — Overview & API Contracts", {
            "overview":      spec.get("overview", ""),
            "api_contracts": spec.get("api_contracts", []),
            "acceptance_criteria": spec.get("acceptance_criteria", []),
        }))
        lines.append(self._json_block("Artifact Paths", state.get("artifact_paths", {})))
        lines.append(self._json_block("QA Report", state.get("test_report", {})))
        lines.append("\nDeploy the app, run smoke test, then output the <submit> block.")
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        return {**state, "deploy_report": data}  # type: ignore[return-value]
