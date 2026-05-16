"""Agent registry — single instances reused across the pipeline."""
from agents.pm import PMAgent
from agents.analyser import AnalyserAgent
from agents.engineer import EngineerAgent
from agents.qa import QAAgent
from agents.reviewer import CodeReviewerAgent
from agents.security import SecurityAgent
from agents.deploy import DeployAgent
from agents.retrospective import RetrospectiveAgent
from agents.spec_analyze import SpecAnalyzeAgent
from agents.task_decompose import TaskDecomposeAgent

AGENTS = {
    "pm":              PMAgent(),
    "analyser":        AnalyserAgent(),
    "engineer":        EngineerAgent(),
    "qa":              QAAgent(),
    "reviewer":        CodeReviewerAgent(),
    "security":        SecurityAgent(),
    "deploy":          DeployAgent(),
    "retrospective":   RetrospectiveAgent(),
    "spec_analyze":    SpecAnalyzeAgent(),
    "task_decompose":  TaskDecomposeAgent(),
}
