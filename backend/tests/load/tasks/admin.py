from __future__ import annotations

from typing import TYPE_CHECKING

from constants import BASE_API_URL, MAX_DELAY, MIN_DELAY

if TYPE_CHECKING:
    from locustfile import BaseAuthorizedUser

import random

from locust import between, task, TaskSet


class AdminBehavior(TaskSet):
    user: BaseAuthorizedUser
    wait_time = between(MIN_DELAY, MAX_DELAY)

    @task(2)
    def view_all_users_admin(self):
        self.user.client.get(
            BASE_API_URL + "/admin/users",
            headers=self.user.auth_headers,
            name="/admin/users"
        )

    @task(1)
    def view_all_categories_admin(self):
        self.user.client.get(
            BASE_API_URL + "/admin/categories",
            headers=self.user.auth_headers,
            name="/admin/categories"
        )

    @task(2)
    def toggle_user_ban_status(self):
        with self.user.client.get(
                BASE_API_URL + "/admin/users",
                headers=self.user.auth_headers,
                name="/admin/users",
                catch_response=True
        ) as response:
            if response.status_code == 200:
                users = response.json().get("items", [])
                if not users:
                    return

                target_user = random.choice(users)
                user_id = target_user["id"]

                endpoint = BASE_API_URL + f"/admin/users/{user_id}/ban" if target_user.get("is_active",
                                                                                           True) else BASE_API_URL + f"/admin/users/{user_id}/unban"
                name_pattern = BASE_API_URL + "/admin/users/[id]/ban" if target_user.get("is_active",
                                                                                         True) else BASE_API_URL + "/admin/users/[id]/unban"

                with self.user.client.patch(
                        endpoint,
                        headers=self.user.auth_headers,
                        name=name_pattern,
                        catch_response=True) as patch_resp:
                    if patch_resp.status_code in (200, 204):
                        patch_resp.success()
                    elif patch_resp.status_code in (400, 404):
                        patch_resp.success()
