from __future__ import annotations

from typing import TYPE_CHECKING

from constants import BASE_API_URL, MAX_DELAY, MIN_DELAY

if TYPE_CHECKING:
    from locustfile import BaseAuthorizedUser

import random
import uuid

from locust import between, task, TaskSet


class RegularUserBehavior(TaskSet):
    user: BaseAuthorizedUser
    wait_time = between(MIN_DELAY, MAX_DELAY)

    @task(4)
    def get_events(self):
        self.user.client.get(
            BASE_API_URL + "/events",
            headers=self.user.auth_headers,
            name="/events"
        )

    @task(2)
    def view_events(self):
        state = self.user.environment.state
        object_ids = []

        for _ in range(random.randrange(1, 4)):
            event_id = state.get_active_event()
            if event_id is None:
                if not object_ids:
                    return
                break
            object_ids.append(event_id)

        payload = {"object_ids": object_ids}

        self.user.client.post(
            BASE_API_URL + "/events/views",
            json=payload,
            headers=self.user.auth_headers,
            name="/events/views"
        )

    @task(4)
    def discover_ticket_categories(self):
        state = self.user.environment.state
        event_id = state.get_active_event()
        if not event_id:
            return

        with self.user.client.get(
                BASE_API_URL + f"/tickets/categories/{event_id}?available_quantity__gte=3",
                headers=self.user.auth_headers,
                name="/tickets/categories/[event_id]",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json().get("results", [])
                new_ids = [item["id"] for item in data if "id" in item]

                if not hasattr(self.user, "discovered_category_ids"):
                    self.user.discovered_category_ids = []

                self.user.discovered_category_ids = [
                    cid for cid in new_ids if cid not in self.user.discovered_category_ids
                ]
            elif response.status_code == 404:
                state.remove_active_event(event_id)
                if hasattr(self.user, "discovered_category_ids"):
                    self.user.discovered_category_ids.clear()
                response.success()
            else:
                response.failure(f"Failed to discover ticket categories: {response.text}")

    @task(3)
    def create_new_order(self):
        if not getattr(self.user, "discovered_category_ids", None):
            return

        category_id = random.choice(self.user.discovered_category_ids)
        payload = {"items": [{"category_id": category_id, "quantity": random.randint(1, 2)}]}

        with self.user.client.post(
                BASE_API_URL + "/orders",
                json=payload,
                headers=self.user.auth_headers | {"X-Idempotency-Key": str(uuid.uuid4())},
                name="/orders",
                catch_response=True,
        ) as response:
            if response.status_code == 201:
                order_id = response.json().get("id")
                if order_id:
                    if not hasattr(self.user, "created_order_ids"):
                        self.user.created_order_ids = []
                    self.user.created_order_ids.append(order_id)
            elif response.status_code in (400, 404):
                if category_id in self.user.discovered_category_ids:
                    self.user.discovered_category_ids.remove(category_id)
                response.success()
            elif response.status_code == 409:
                response.success()
            else:
                response.failure(f"Failed to create order: {response.text}")

    @task(2)
    def pay_existing_order(self):
        if not getattr(self.user, "created_order_ids", None):
            return

        order_id = self.user.created_order_ids.pop(0)
        with self.user.client.patch(
            BASE_API_URL + f"/orders/{order_id}/pay",
            headers=self.user.auth_headers | {"X-Idempotency-Key": str(uuid.uuid4())},
            name="/orders/[id]/pay",
            catch_response=True
        ) as response:
            if 200 <= response.status_code < 300:
                response.success()
            else:
                self.user.created_order_ids.insert(0, order_id)
                response.failure(response.text)
