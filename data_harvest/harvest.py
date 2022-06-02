import tweepy
import couchdb as DB
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# rename this import to reference the key file used
import INFO as INFO
from sa2_data import *

# Twitter filter Stream API streamer using geolocation filtering for Melbourne
class tweet(tweepy.Stream):
    def __init__(self, consumer_key, consumer_secret, access_token, access_secret):
        super(tweet, self).__init__(consumer_key, consumer_secret, access_token, access_secret)
        # CouchDB setup
        self.__userName = INFO.USERNAME
        self.__passWord = INFO.PASSWORD
        self.__url = f'http://{self.__userName}:{self.__passWord}@{INFO.IP_ADDR}:{INFO.PORT}/'
        print("Connecting to server...")
        self.server = DB.Server(self.__url)
        self.db = self.server['twitter_new']
        print("Connected to server")

        # load suburb data
        self.sa2_main16_df = load_sa2_data()
        self.analyser = SentimentIntensityAnalyzer()
        print("Harvester setup complete")

    def on_status(self, status):  # get the tweets from tweeter
        data = status._json
        print(f"Filtered tweet id: {data['id']}")
        tweet_info = self.prepare_tweet_document(data, status)
        self.store_tweets(tweet_info)

    def prepare_tweet_document(self, data, status):
        # Extract the text from the tweet
        text = self.get_tweet_text(data, status)
        # store the document in the database as a dictionary with keys {tweet, sentiment, sa2}
        tweet_info = dict()
        tweet_info['_id'] = str(data['id'])
        tweet_info['type'] = 'stream'
        tweet_info['tweet'] = data
        sentiment = self.analyser.polarity_scores(text)
        tweet_info['sentiment'] = sentiment
        coords = get_tweet_coordinates(data)
        if coords is not None:
            tweet_info['sa2'] = get_sa2_main16(coords, self.sa2_main16_df)
        return tweet_info

    def get_tweet_text(self, data, status):
        try:
            if 'extended_tweet' in data.keys():
                text = data['extended_tweet']['full_text']
            elif 'full_text' in status.retweeted_status.extended_tweet.keys():
                text = status.retweeted_status.extended_tweet['full_text']
            else:
                text = data['text']
        except (KeyError, AttributeError):
            print("Warning: Tweet KeyError - using default tweet text")
            text = data['text']
        return text

    def store_tweets(self, tweets):
        try:
            doc_id, doc_rev = self.db.save(tweets)
            print(f"Document stored in database: id: {doc_id}, rev: {doc_rev}")
        except DB.http.ResourceConflict:
            print(f"Document already present in database. Not updated")


if __name__ == '__main__':
    bear_token = INFO.BEAR_TOKEN
    consumer_key = INFO.API_KEY
    consumer_secret = INFO.KEY_SECRET
    access_token = INFO.ACCESS_TOKEN
    access_secret = INFO.TOKEN_SECRET

    t = tweet(consumer_key, consumer_secret, access_token, access_secret)
    print("Setup complete")
    # coordinates for Melbourne based on a bounding box for the Greater Melbourne region
    coordinates = [144.33363404800002, -38.50298801599996, 145.8784120140001, -37.17509899299995]

    print("Filtering tweets...")
    t.filter(locations=coordinates)
