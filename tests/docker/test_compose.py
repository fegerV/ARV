import os
import pytest

pytestmark = pytest.mark.docker

@pytest.mark.skipif(os.environ.get("DOCKER_TESTS") != "1", reason="Set DOCKER_TESTS=1 to run Docker tests.")
def test_compose_file_exists():
    assert os.path.exists("docker-compose.test.yml")
