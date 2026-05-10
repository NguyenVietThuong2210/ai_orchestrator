"""Agent registry — single instances reused across the pipeline."""
from agents.pm import PMAgent
from agents.analyser import AnalyserAgent
from agents.engineer import EngineerAgent
from agents.qa import QAAgent

AGENTS = {
    "pm":       PMAgent(),
    "analyser": AnalyserAgent(),
    "engineer": EngineerAgent(),
    "qa":       QAAgent(),
}
