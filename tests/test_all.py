import json
import logging
import responses

import pytest

import orm
from api.schemas.chat import ChatCreateSchema

logger = logging.getLogger('sqlalchemy.engine.Engine')
logger.setLevel(logging.NOTSET)


class TestAll:

    async def test_create_user(self, client):
        response = await client.post(
            "/api/v1/register",
            json={
                "username": "TestUser",
                "email": "test@email.com",
                "password": "string",
            }
        )
        print("############")
        response_json = response.json()
        print(f"response: {response_json}")
        print("############")
        assert response.status_code == 200
        assert response_json.get('username') == "TestUser"
        assert response_json.get('email') == "test@email.com"

    async def test_create_chat_with_auth(self, client, session, mock_validator):
        v_host = "127.0.0.1"
        v_port = 8002

        mocked_response = {
            "status": 200,
            "reply": {
                    "text": "The last transaction has the ID '8dab83aebb56fa391f7c70fc5ab01b0154810e10b3a806d0c9a79bce7ef5574f'. It was not a coinbase transaction. The transaction occurred at block height 839889 and was timestamped at 1713856318. The total input amount for this transaction was 36046, while the total output amount was 1000.",
                    "miner_id": "1"
            }
        }

        mock_validator.add(
            responses.POST,
            f"http://{v_host}:{v_port}/api/text_query",
            json=mocked_response["reply"],
            status=mocked_response["status"]
        )

        user_data = {
            "username": "TestUse3121r",
            "email": "tes33t@email.com",
            "password": "string33",
        }
        register_result = await client.post("/api/v1/register", json=user_data)

        logging.debug("register_result: {}".format(register_result))
        # 2. Login to get an access token
        login_data = {
            "username": "TestUse3121r",
            "password": "string33",
        }
        response = await client.post("/api/v1/token", data=login_data)
        assert response.status_code == 200
        access_token = response.json()["access_token"]

        # 3. Set the Authorization header
        client.headers = {"Authorization": f"Bearer {access_token}"}

        validator = orm.Validator(name="smith", uid=0, is_active=True, ip="127.0.0.1", port=8002)
        session.add(validator)
        await session.commit()
        await session.refresh(validator)

        # 4. Create chat data
        chat_data = ChatCreateSchema(message_content="test")

        # 5. Send the request to create the chat
        response = await client.post("/api/v1/chats", json=chat_data.dict())

        # 6. Assert successful creation
        assert response.status_code == 200

