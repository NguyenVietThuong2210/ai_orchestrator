"""
Claude tool definitions (JSON schema) — one submit tool per agent.
Role-scoped: each agent only receives its own tool list.
"""
from __future__ import annotations

# ── PM ────────────────────────────────────────────────────────────────────────
PM_TOOLS: list[dict] = [
    {
        "name": "submit_plan",
        "description": "Submit the final structured task list. Call this exactly once when done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":          {"type": "string"},
                            "title":       {"type": "string"},
                            "description": {"type": "string"},
                            "priority":    {"type": "integer", "minimum": 1, "maximum": 5},
                            "status":      {"type": "string", "enum": ["pending"]},
                        },
                        "required": ["id", "title", "description", "priority", "status"],
                    },
                }
            },
            "required": ["tasks"],
        },
    }
]

# ── Analyser ──────────────────────────────────────────────────────────────────
ANALYSER_TOOLS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read a file from the project directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "submit_spec",
        "description": "Submit the completed technical specification. Call this exactly once when done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "overview":             {"type": "string"},
                "components":           {"type": "array", "items": {"type": "object"}},
                "api_contracts":        {"type": "array", "items": {"type": "object"}},
                "data_models":          {"type": "array", "items": {"type": "object"}},
                "risks":                {"type": "array", "items": {"type": "object"}},
                "acceptance_criteria":  {"type": "array", "items": {"type": "string"}},
            },
            "required": ["overview", "components", "api_contracts",
                         "data_models", "risks", "acceptance_criteria"],
        },
    },
]

# ── Engineer ──────────────────────────────────────────────────────────────────
ENGINEER_TOOLS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file in ARTIFACT_DIR.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "Relative path inside ARTIFACT_DIR"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_shell",
        "description": "Run a shell command (e.g. pip install, mkdir). Working dir = ARTIFACT_DIR.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "submit_implementation",
        "description": "Submit the completed implementation. Call this exactly once when all files are written.",
        "input_schema": {
            "type": "object",
            "properties": {
                "artifact_paths": {
                    "type": "object",
                    "description": "Map of filename → relative path inside ARTIFACT_DIR",
                    "additionalProperties": {"type": "string"},
                },
                "summary": {"type": "string"},
            },
            "required": ["artifact_paths", "summary"],
        },
    },
]

# ── QA ────────────────────────────────────────────────────────────────────────
QA_TOOLS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read a source or test file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "run_shell",
        "description": "Run tests or validation commands. Working dir = ARTIFACT_DIR.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "submit_test_report",
        "description": "Submit the final test report. Call this exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status":  {"type": "string", "enum": ["pass", "fail-minor", "fail-major"]},
                "summary": {"type": "string"},
                "passed":  {"type": "array", "items": {"type": "string"}},
                "failed":  {"type": "array", "items": {"type": "string"}},
                "defects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":          {"type": "string"},
                            "severity":    {"type": "string", "enum": ["minor", "major"]},
                            "description": {"type": "string"},
                            "file":        {"type": "string"},
                            "line":        {"type": "integer"},
                        },
                        "required": ["id", "severity", "description"],
                    },
                },
            },
            "required": ["status", "summary", "passed", "failed", "defects"],
        },
    },
]

AGENT_TOOLS: dict[str, list[dict]] = {
    "pm":       PM_TOOLS,
    "analyser": ANALYSER_TOOLS,
    "engineer": ENGINEER_TOOLS,
    "qa":       QA_TOOLS,
}
