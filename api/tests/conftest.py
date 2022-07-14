# Copyright (C) 2022, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import pytest
import pytest_asyncio
import requests
from app.main import app
from httpx import AsyncClient


@pytest.fixture(scope="session")
def mock_classification_image(tmpdir_factory):
    url = (
        "https://upload.wikimedia.org/wikipedia/commons/a/a6/The_Rim_Fire_in_the_Stanislaus_National_Forest_"
        "near_in_California_began_on_Aug._17%2C_2013-0004.jpg"
    )
    return requests.get(url).content


@pytest_asyncio.fixture(scope="function")
async def test_app_asyncio():
    # for httpx>=20, follow_redirects=True (cf. https://github.com/encode/httpx/releases/tag/0.20.0)
    async with AsyncClient(app=app, base_url="http://test", follow_redirects=True) as ac:
        yield ac  # testing happens here
