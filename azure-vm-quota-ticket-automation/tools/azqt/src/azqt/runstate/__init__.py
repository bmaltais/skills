"""Per-run state for azqt: run id generation and state directory resolution.

This package holds the logic for starting a Run (``init-run``): generating a
unique run id, resolving where that run's on-disk state (currently just its
audit log file) lives, and creating the run-start audit entry.
"""
