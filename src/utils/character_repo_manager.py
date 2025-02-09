import boto3
import os

REGION = os.environ.get("REGION", "us-east-1")
CHARACTER_TABLE = "characters"

class CharacterManager:

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=REGION)
        self.table = self.dynamodb.Table(CHARACTER_TABLE)

    async def get_character(self, character_id:str) -> dict:
        """
        Retrieves the character from DynamoDB table
        Args:
            character_id: The ID of the character
        Returns:
            dict: The character
        """

        response = self.table.get_item(Key={'id': character_id})

        item = response['Item']

        return item