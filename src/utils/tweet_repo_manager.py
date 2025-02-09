import boto3
import httpx
from datetime import datetime, UTC
import os
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from typing import Sequence, List

DEBUG_MODE = os.environ.get("DEBUG_MODE", "true") == "true"
REGION = os.environ.get("REGION", "us-east-1")
TWITTER_CONVERSATIONS_TABLE = "twitter-conversations"

def __convert_post_to_message(character_name: str, post: dict)->BaseMessage:
    """
    Converts a tweet post dictionary into a BaseMessage object, using the provided character name.

    Args:
        character_name (str): The name of the character associated with the tweet post.
        post (dict): A dictionary containing information about a single tweet post.

    Returns:
        BaseMessage: A BaseMessage object representing the tweet post.
    """
    if post["user"] == character_name:
        return AIMessage(content=post["content"], name=character_name)
    else:
        return HumanMessage(content=post["content"], name=character_name)


def __convert_posts_to_messages(character_name: str, posts: Sequence[dict])->List[BaseMessage]:
    """
    Converts a sequence of tweet post dictionaries into a list of BaseMessage objects, 
    using the provided character name.
    
    Args:
        character_name (str): The name of the character associated with the tweet posts.
        posts (Sequence[dict]): A sequence of tweet post dictionaries, each containing information 
            about a single tweet post.
    
    Returns:
        List[BaseMessage]: A list of BaseMessage objects representing the tweet posts.
    """
        
    return [
        __convert_post_to_message(character_name, post)
        for post in posts
    ]


class TweetConversationManager:

    def __init__(self, character_id: str, character_name: str):
        self.character_name = character_name    
        self.character_id = character_id
        self.http_client = httpx.AsyncClient()
        self.dynamodb = boto3.resource('dynamodb', region_name=REGION)
        self.table = self.dynamodb.Table(TWITTER_CONVERSATIONS_TABLE)

    async def new_post(
            self,
            tweet_id: str,
            tweet_content: str,
        ):
        """
        Posts a tweet to DynamoDB table with character_id and auto-generated tweet_id
        Args:
            tweet_id: The ID of the tweet
            tweet_content: The content of the tweet
        Returns:
            str: Confirmation message with the tweet_id
        """        
        timestamp = datetime.now(UTC).isoformat()
        
        item = {
            'character_id': self.character_id,
            'conversation_id': tweet_id,
            'op_user': self.character_name,
            'posts': [
                {
                    'tweet_id': tweet_id,
                    'user': self.character_name,
                    'content': tweet_content,
                    'meta': {},
                    'timestamp': timestamp
                }
            ],
            'created_date': timestamp
        }
        
        self.table.put_item(Item=item)


    async def new_foreign_conversation(
            self,
            op_user: str,
            conversation_id: str,
            posts: str,
        ):
        """
        Posts a tweet to DynamoDB table with character_id and auto-generated tweet_id
        Args:
            op_user: The handle of the original poster
            posts: List of posts in the conversation
        """        
        timestamp = datetime.now(UTC).isoformat()
        
        item = {
            'character_id': self.character_id,
            'conversation_id': conversation_id,
            'op_user': op_user,
            'posts': posts,
            'created_date': timestamp
        }
        
        self.table.put_item(Item=item)


    async def update_conversation(
            self,
            conversation_id: str,
        ):
        """
        Updates the conversation in DynamoDB table with the latest tweet
        Args:
            conversation_id: The ID of the conversation
        Returns:
            str: Confirmation message
        """

        response = self.table.get_item(Key={'character_id': self.character_id, 'conversation_id': conversation_id})
        item = response['Item']

        new_posts = [] # TODO: Add code to search twitter API and update with new posts
        
        item['posts'] += new_posts

        self.table.put_item(Item=item)
        return
    

    async def get_conversation(
            self,
            conversation_id: str,
        ):
        """
        Retrieves the conversation from DynamoDB table
        Args:
            conversation_id: The ID of the conversation
        Returns:
            dict: The conversation
        """

        response = self.table.get_item(Key={'character_id': self.character_id, 'conversation_id': conversation_id})
        item = response['Item']
        return item 


    async def get_latest_created_posts(
            self,
            limit: int = 20,
            as_messages: bool = False
        ):
        """
        Retrieves the latest posts from DynamoDB table
        Args:
            limit: The number of posts to retrieve
        Returns:
            list: The latest posts
        """

        response = self.table.query(
            KeyConditionExpression='character_id = :character_id',
            ExpressionAttributeValues={
                ':character_id': self.character_id,
                ':char_name': self.character_name
            },
            FilterExpression='op_user = :char_name',
            ScanIndexForward=False,
            Select='ALL_ATTRIBUTES',
            Limit=limit
        )
        items = sorted(response['Items'], 
                        key=lambda x: x['conversation_id'],
                        reverse=True)            
        
        if as_messages:
            return __convert_posts_to_messages([item['posts'][0] for item in items])
        else:
            return [item['posts'][0] for item in items]

