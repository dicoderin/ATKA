import tweepy
from openai import OpenAI
import logging
import time

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Autentikasi Twitter
BEARER_TOKEN = "YOUR_BEARER_TOKEN"
TWITTER_CLIENT = tweepy.Client(
    consumer_key="YOUR_API_KEY",
    consumer_secret="YOUR_API_SECRET",
    access_token="YOUR_ACCESS_TOKEN",
    access_token_secret="YOUR_ACCESS_SECRET",
    wait_on_rate_limit=True
)

# Autentikasi OpenAI
OPENAI_CLIENT = OpenAI(api_key="YOUR_OPENAI_KEY")

class KaitoAICommentBot(tweepy.StreamingClient):
    def __init__(self, bearer_token, **kwargs):
        super().__init__(bearer_token, **kwargs)
        self.target_username = "_kaitoai"
        self.replied_tweets = set()
    
    def generate_comment(self, tweet_text):
        try:
            prompt = f"Buat komentar relevan dalam 1-2 kalimat untuk tweet: '{tweet_text}'. Gunakan bahasa santai dan tambahkan 1-2 hashtag."
            
            response = OPENAI_CLIENT.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Anda AI ahli yang memberikan komentar menarik tentang teknologi."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating comment: {e}")
            return None

    def on_tweet(self, tweet):
        try:
            # Cek retweet
            if tweet.referenced_tweets and any(t.type == 'retweeted' for t in tweet.referenced_tweets):
                return
                
            # Cek user target
            user = [u for u in self.includes['users'] if u.id == tweet.author_id][0]
            if user.username.lower() != self.target_username.lower():
                return
                
            if tweet.id in self.replied_tweets:
                return
                
            logger.info(f"New tweet detected: {tweet.text}")
            
            # Generate komentar
            comment = self.generate_comment(tweet.text)
            if comment:
                reply_text = f"@{user.username} {comment}"
                TWITTER_CLIENT.create_tweet(
                    text=reply_text[:280],  # Pastikan tidak melebihi batas karakter
                    in_reply_to_tweet_id=tweet.id
                )
                logger.info(f"Replied to tweet {tweet.id}")
                self.replied_tweets.add(tweet.id)
                time.sleep(30)
                
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")

if __name__ == "__main__":
    stream = KaitoAICommentBot(BEARER_TOKEN)
    
    # Hapus rules lama
    rules = stream.get_rules().data or []
    if rules:
        stream.delete_rules([rule.id for rule in rules])
    
    # Tambah rule baru
    stream.add_rules(tweepy.StreamRule(f"from:{stream.target_username}"))
    
    logger.info("Starting stream...")
    stream.filter(
        expansions=["author_id"],
        user_fields=["username"],
        tweet_fields=["referenced_tweets"]
    )
