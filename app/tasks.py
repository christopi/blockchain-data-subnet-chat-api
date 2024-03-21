import asyncio
import logging

import requests
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from orm import Validator
from orm.session_manager import DatabaseSessionManager
from app.settings import settings

logging.basicConfig(level=logging.DEBUG)


async def load_data_task(db_manager: DatabaseSessionManager):
    while True:
        try:
            # Make a request to the remote endpoint
            headers = {
                "accept": "application/json",
                "x-api-key": settings.hotkeys_api_key
            }
            logging.debug('Fetching validators')

            response = requests.get(f"{settings.hotkeys_api_url}/validators/endpoints", headers=headers)
            data = response.json()

            validators = []
            for item in data:
                validator = {
                    "uid": int(item["uid"]),
                    "name": item["name"],
                    "hotkey": item["hotkey"],
                    "ip": item["ip"],
                    "port": item["port"]
                }
                validators.append(validator)

            response_uids = {v["uid"] for v in validators}

            # Upsert the validators into the database
            async with db_manager.session() as db:
                await db.execute(
                    update(Validator)
                    .where(Validator.uid.notin_(response_uids))
                    .values(is_active=False)
                )

                for validator in validators:
                    stmt = insert(Validator).values(**validator).on_conflict_do_update(
                        index_elements=[Validator.uid],
                        set_={**validator, "is_active": True}
                    )
                    await db.execute(stmt)
                await db.commit()

            # Sleep for 10 minutes before the next iteration
            logging.debug('Updated validators, next run in 10 minutes')
            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Failed to fetch validators: {e}")
