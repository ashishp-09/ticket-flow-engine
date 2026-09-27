from __future__ import annotations

from typing import TYPE_CHECKING

from constants import BASE_API_URL, MAX_DELAY, MIN_DELAY

if TYPE_CHECKING:
    from locustfile import BaseAuthorizedUser

import random

from locust import between, task, TaskSet


class ModeratorBehavior(TaskSet):
    user: BaseAuthorizedUser
    wait_time = between(MIN_DELAY, MAX_DELAY)

    @task(3)
    def view_events_for_moderation(self):
        self.user.client.get(
            BASE_API_URL + "/moderation/events",
            headers=self.user.auth_headers,
            name="/moderation/events"
        )

    @task(2)
    def view_users_for_verification(self):
        self.user.client.get(
            BASE_API_URL + "/moderation/users",
            headers=self.user.auth_headers,
            name="/moderation/users"
        )

    @task(2)
    def moderate_event(self):
        state = self.user.environment.state

        with self.user.client.get(
                BASE_API_URL + "/moderation/events",
                headers=self.user.auth_headers,
                name="/moderation/events",
                catch_response=True
        ) as response:
            if response.status_code == 200:
                events_list = response.json().get("results", [])

                if not events_list:
                    return

                target_event = random.choice(events_list)
                event_id = target_event["id"]

                with self.user.client.patch(
                        BASE_API_URL + f"/moderation/events/{event_id}",
                        headers=self.user.auth_headers,
                        json={"result": True},
                        name=BASE_API_URL + "/moderation/events/[id]",
                        catch_response=True
                ) as patch_resp:
                    if patch_resp.status_code == 200:
                        state.add_active_event(event_id)
                    elif patch_resp.status_code in (400, 404):
                        patch_resp.success()

    @task(2)
    def verify_user(self):
        with self.user.client.get(
                BASE_API_URL + "/moderation/users",
                headers=self.user.auth_headers,
                name="/moderation/users",
                catch_response=True
        ) as response:
            if response.status_code == 200:
                users_list = response.json().get("results", [])
                if users_list:
                    user_id = random.choice(users_list)["id"]
                    with self.user.client.patch(
                            BASE_API_URL + f"/moderation/users/{user_id}",
                            headers=self.user.auth_headers,
                            json={"result": random.choice([True, False])},
                            name=BASE_API_URL + "/moderation/users/[id]",
                            catch_response=True
                    ) as patch_resp:
                        if patch_resp.status_code in (400, 404):
                            patch_resp.success()
