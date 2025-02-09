from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.runnables import RunnableConfig
from utils.tweet_repo_manager import TweetConversationManager
import uuid
import logging
import asyncio
import httpx
import os


search_the_internet = DuckDuckGoSearchResults()

@tool
async def post_tweet(tweet: str, config: RunnableConfig) -> str:
    """
    Posts a tweet.
    """
    character_id = config["configurable"]["character_id"]
    character_name = config["configurable"]["character_name"]

    logging.info("Posting tweet: " + tweet)
    ## TODO: Add post tweet to twitter code
    response = {
        "data": {
            "id": str(uuid.uuid4()),
            "text": tweet,
        }
    }

    await TweetConversationManager(
        character_id=character_id,
        character_name=character_name,
    ).new_post(
        tweet_id=response["data"]["id"],
        tweet_content=tweet,
    )
    return "Tweet posted"