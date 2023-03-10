import pytest


def pytest_addoption(parser):
    parser.addoption("--cloud", action="store", default="aws")


@pytest.fixture
def cloud(request):
    return request.config.getoption("--cloud")
