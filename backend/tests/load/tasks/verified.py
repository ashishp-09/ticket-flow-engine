from __future__ import annotations

from typing import TYPE_CHECKING

from constants import BASE_API_URL, MAX_DELAY, MIN_DELAY

if TYPE_CHECKING:
    from locustfile import BaseAuthorizedUser

import random
import uuid
from datetime import datetime, timedelta, timezone

from locust import between, task, TaskSet

from src.modules.event.models import EventFormat


class VerifiedUserBehavior(TaskSet):
    user: BaseAuthorizedUser
    wait_time = between(MIN_DELAY, MAX_DELAY)

    @task(1)
    def full_event_lifecycle(self):
        state = self.user.environment.state
        chosen_category_id = state.get_event_category()
        if not chosen_category_id:
            return

        format = random.choice([EventFormat.ONLINE, EventFormat.OFFLINE])
        started_at = (datetime.now(timezone.utc) + timedelta(days=random.randint(1, 30))).isoformat()

        payload_event = {
            "category_id": chosen_category_id,
            "title": f"Load Test Title {uuid.uuid4().hex[:12]}",
            "description": "Valid non-empty description for performance testing purposes",
            "format": format,
            "started_at": started_at,
            "address": "Valid City, Test Street, 42" if format == EventFormat.OFFLINE else None
        }

        with self.user.client.post(
                BASE_API_URL + "/events",
                headers=self.user.auth_headers,
                json=payload_event,
                name="/events [Create]",
                catch_response=True
        ) as response:
            if response.status_code != 201:
                response.failure(response.text)
                return
            event_id = response.json().get("id")

        if not event_id:
            return

        all_categories_created = True
        categories_count = random.randint(1, 3)
        for _ in range(categories_count):
            payload_ticket = {
                "event_id": event_id,
                "name": f"Sector {uuid.uuid4().hex[:4].upper()}",
                "price": random.randint(100, 5000),
                "total_quantity": random.randint(1000, 5000)
            }
            with self.user.client.post(
                    BASE_API_URL + "/tickets/categories",
                    headers=self.user.auth_headers,
                    json=payload_ticket,
                    name="/tickets/categories",
                    catch_response=True
            ) as ticket_resp:
                if ticket_resp.status_code != 201:
                    all_categories_created = False
                    ticket_resp.failure(f"Ticket category creation failed: {ticket_resp.text}")

        if all_categories_created:
            self.user.client.patch(
                BASE_API_URL + f"/events/{event_id}/publish",
                headers=self.user.auth_headers,
                name="/events/[id]/publish"
            )
