from datetime import datetime, timedelta, timezone

from fastapi import status

from src.modules.event.models import EventState, EventFormat


class TestTicketCategories:
    user_role = "verified_user"

    async def test_get_all_categories_success_owner(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            user = await create_model_factory(uow, "user", id=1, email="owner@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=100, name="Music Unique 1")
            await create_model_factory(
                uow,
                "event",
                id=10,
                user_id=user.id,
                state=EventState.APPROVED,
                title="Title 10",
                description="Desc 10",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=100,
            )
            await create_model_factory(
                uow,
                "ticket_category",
                id=1,
                event_id=10,
                name="Unique Get Owner Category",
                price=100,
                total_quantity=100
            )
            await uow.commit()

        response = await api_client.get("/tickets/categories/10")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    async def test_get_all_categories_event_not_found(self, api_client):
        response = await api_client.get("/tickets/categories/2147483646")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_all_categories_not_owner_not_upcoming(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="owner2@test.com", password="pwd")
            await create_model_factory(uow, "user", id=2, email="other@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=101, name="Music Unique 2")
            await create_model_factory(
                uow,
                "event",
                id=11,
                user_id=2,
                state=EventState.DRAFT,
                title="Title 11",
                description="Desc 11",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=101
            )
            await uow.commit()

        response = await api_client.get("/tickets/categories/11")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_ticket_category_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            user = await create_model_factory(uow, "user", id=1, email="owner3@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=102, name="Music Unique 3")
            await create_model_factory(
                uow,
                "event",
                id=12,
                user_id=user.id,
                state=EventState.DRAFT,
                title="Title 12",
                description="Desc 12",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=102,
            )
            await uow.commit()

        payload = {
            "event_id": 12,
            "name": "Unique New VIP Category",
            "price": 500,
            "total_quantity": 50
        }
        response = await api_client.post("/tickets/categories", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    async def test_create_ticket_category_event_not_found(self, api_client):
        payload = {
            "event_id": 999,
            "name": "Nonexistent Event Category",
            "price": 500,
            "total_quantity": 50
        }
        response = await api_client.post("/tickets/categories", json=payload)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_ticket_category_not_owner(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="owner4@test.com", password="pwd")
            await create_model_factory(uow, "user", id=2, email="other_post@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=103, name="Music Unique 4")
            await create_model_factory(
                uow,
                "event",
                id=13,
                user_id=2,
                state=EventState.DRAFT,
                title="Title 13",
                description="Desc 13",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=103
            )
            await uow.commit()

        payload = {
            "event_id": 13,
            "name": "Stranger Category",
            "price": 500,
            "total_quantity": 50
        }
        response = await api_client.post("/tickets/categories", json=payload)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_ticket_category_wrong_event_state(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            user = await create_model_factory(uow, "user", id=1, email="owner5@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=104, name="Music Unique 5")
            await create_model_factory(
                uow,
                "event",
                id=14,
                user_id=user.id,
                state=EventState.APPROVED,
                title="Title 14",
                description="Desc 14",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=104
            )
            await uow.commit()

        payload = {
            "event_id": 14,
            "name": "Wrong State Category",
            "price": 500,
            "total_quantity": 50
        }
        response = await api_client.post("/tickets/categories", json=payload)
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_update_ticket_category_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            user = await create_model_factory(uow, "user", id=1, email="owner6@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=105, name="Music Unique 6")
            await create_model_factory(
                uow,
                "event",
                id=15,
                user_id=user.id,
                state=EventState.DRAFT,
                title="Title 15",
                description="Desc 15",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=105
            )
            await create_model_factory(
                uow,
                "ticket_category",
                id=2,
                event_id=15,
                name="Unique Patch Target Category",
                price=100,
                total_quantity=100
            )
            await uow.commit()

        payload = {
            "name": "Unique Patched Category Name",
            "price": 150
        }
        response = await api_client.patch("/tickets/categories/2", json=payload)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_update_ticket_category_not_found(self, api_client):
        payload = {
            "name": "Nonexistent Category Name"
        }
        response = await api_client.patch("/tickets/categories/999", json=payload)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_ticket_category_not_owner(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="owner7@test.com", password="pwd")
            await create_model_factory(uow, "user", id=2, email="other_patch@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=106, name="Music Unique 7")
            await create_model_factory(
                uow,
                "event",
                id=16,
                user_id=2,
                state=EventState.DRAFT,
                title="Title 16",
                description="Desc 16",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=106
            )
            await create_model_factory(
                uow,
                "ticket_category",
                id=3,
                event_id=16,
                name="Stranger Patch Category",
                price=100,
                total_quantity=100
            )
            await uow.commit()

        payload = {
            "name": "Malicious Name Update"
        }
        response = await api_client.patch("/tickets/categories/3", json=payload)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_ticket_category_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            user = await create_model_factory(uow, "user", id=1, email="owner8@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=107, name="Music Unique 8")
            await create_model_factory(
                uow,
                "event",
                id=17,
                user_id=user.id,
                state=EventState.DRAFT,
                title="Title 17",
                description="Desc 17",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=107
            )
            await create_model_factory(
                uow,
                "ticket_category",
                id=4,
                event_id=17,
                name="Unique Delete Target Category",
                price=100,
                total_quantity=100
            )
            await uow.commit()

        response = await api_client.delete("/tickets/categories/4")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_ticket_category_not_found(self, api_client):
        response = await api_client.delete("/tickets/categories/2147483646")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_ticket_category_not_owner(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="owner9@test.com", password="pwd")
            await create_model_factory(uow, "user", id=2, email="other_delete@test.com", password="pwd")
            await create_model_factory(uow, "event_category", id=108, name="Music Unique 9")
            await create_model_factory(
                uow,
                "event",
                id=18,
                user_id=2,
                state=EventState.DRAFT,
                title="Title 18",
                description="Desc 18",
                format=EventFormat.ONLINE,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
                category_id=108
            )
            await create_model_factory(
                uow,
                "ticket_category",
                id=5,
                event_id=18,
                name="Stranger Delete Category",
                price=100,
                total_quantity=100
            )
            await uow.commit()

        response = await api_client.delete("/tickets/categories/5")
        assert response.status_code == status.HTTP_404_NOT_FOUND
