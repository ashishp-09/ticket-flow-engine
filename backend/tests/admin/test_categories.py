import pytest
from fastapi import status


class TestAdminCategories:
    user_role = "admin"

    async def test_create_category_success(self, api_client):
        payload = {"name": "New Category"}
        response = await api_client.post("/admin/categories", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "New Category"

    @pytest.mark.parametrize(
        "payload",
        [
            {"name": ""},
            {"name": "   "},
            {"name": "A" * 300},
            {"name": "Valid", "extra_field": "forbidden"},
            {},
        ],
    )
    async def test_create_category_validation_errors(self, api_client, payload):
        response = await api_client.post("/admin/categories", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_create_category_non_existent_parent(self, api_client):
        payload = {"name": "Sub Category", "parent_id": 2147483647}
        response = await api_client.post("/admin/categories", json=payload)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_sub_category_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "event_category", id=100, name="Parent Category")
            await uow.commit()

        payload = {"name": "Sub Category", "parent_id": 100}
        response = await api_client.post("/admin/categories", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "Sub Category"

    async def test_create_category_duplicate(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "event_category", id=200, name="Unique Name")
            await uow.commit()

        payload = {"name": "Unique Name"}
        response = await api_client.post("/admin/categories", json=payload)
        assert response.status_code == status.HTTP_409_CONFLICT


class TestAdminGetCategories:
    user_role = "admin"

    async def test_admin_get_categories_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await uow.commit()

        response = await api_client.get("/admin/categories?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["results"][0]["name"] == "Music"

    @pytest.mark.parametrize("search_query", ["music", "MUSIC", "MuSiC"])
    async def test_admin_get_categories_case_insensitive(self, api_client, setup_uow, create_model_factory, search_query):
        async with setup_uow as uow:
            await create_model_factory(uow, "event_category", id=300, name="Music")
            await uow.commit()

        response = await api_client.get(f"/admin/categories?limit=10&offset=0&name__icontains={search_query}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 1
