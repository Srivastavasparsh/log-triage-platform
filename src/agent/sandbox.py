import subprocess
from pathlib import Path
import docker
from docker.errors import DockerException


def run_tests_in_sandbox(test_file_path: str) -> tuple[bool, str]:
    project_root = str(Path.cwd().resolve())
    command = f"pytest {test_file_path} -v"

    try:
        client = docker.from_env()
        output = client.containers.run(
            image="python:3.12-slim",
            command=f"sh -c 'pip install -q pytest && {command}'",
            volumes={project_root: {"bind": "/workspace", "mode": "ro"}},
            working_dir="/workspace",
            network_disabled=True,
            remove=True,
        )
        return True, output.decode("utf-8")

    except docker.errors.ContainerError as error:
        logs = error.stderr.decode("utf-8") if error.stderr else str(error)
        return False, logs

    except DockerException:
        # Fallback to local venv pytest if Docker Desktop is not running
        result = subprocess.run(
            ["pytest", test_file_path, "-v"],
            capture_output=True,
            text=True,
        )
        combined_output = f"{result.stdout}\n{result.stderr}".strip()
        return result.returncode == 0, combined_output