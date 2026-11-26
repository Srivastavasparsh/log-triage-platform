from pydantic import BaseModel


class CrashContext(BaseModel):
    service_name: str
    file_path: str
    line_number: int
    function_name: str
    error_type: str
    error_message: str
    stack_trace: str


class DiagnosisPlan(BaseModel):
    root_cause: str
    proposed_fix_summary: str
    patched_code: str


class VerificationResult(BaseModel):
    passed: bool
    test_output: str
    attempt_number: int