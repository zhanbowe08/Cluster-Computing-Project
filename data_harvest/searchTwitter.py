import tweepy
import INFO_4 as INFO
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import geopandas as gpd
from shapely.geometry import Point
import couchdb as DB
import time
from datetime import date

class search(tweepy.API):
    def __init__(self, consumer_key, consumer_secret, access_token, access_secret):
        super(search, self).__init__()
        self.__userName = 'admin'
        self.__passWord = 'password'
        self.__url = 'http://' + self.__userName + ':' + self.__passWord + '@172.26.131.244:5984/'
        print("Connecting to server...")

        self.server = DB.Server(self.__url)
        print("Connected to server")
        self.db = self.server['twitter_new']

        self.analyser = SentimentIntensityAnalyzer()
        self.__auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        self.__auth.set_access_token(access_token, access_secret)
        self.api = tweepy.API(self.__auth, wait_on_rate_limit=True)
        self.sa2_main16_df = load_sa2_data()
        self.today = date.today()
        print("Harvester setup complete")

    def search_tweet(self):
        query = 'place:melbourne'
        date = int(self.today.strftime("%Y%m%d"))
        start = str(date - 100) + "0000"
        label = '30days'
        status = tweepy.Cursor(self.api.search_30_day,
                               label=label,
                               query=query,
                               fromDate=start,
                               maxResults=10
                               ).pages()
        for each in status:
            for tweet in each:
                tweet_info = dict()
                tweet = tweet._json
                try:
                    if 'extended_tweet' in tweet.keys():
                        text = tweet['extended_tweet']['full_text']
                    else:
                        text = tweet['text']
                except (KeyError, AttributeError):
                    print("Tweet KeyError - using default tweet text")
                    text = tweet['text']
                print(f"Tweet id: {tweet['id']}, date created: {tweet['created_at']}")

                tweet_info['_id'] = str(tweet['id'])
                tweet_info['type'] = 'search'
                tweet_info['tweet'] = tweet
                sentiment = self.analyser.polarity_scores(text)
                tweet_info['sentiment'] = sentiment

                coords = get_tweet_coordinates(tweet)

                if coords is not None:
                    tweet_info['sa2'] = get_sa2_main16(coords, self.sa2_main16_df)

                # print(tweet_info)
                self.store_tweets(tweet_info)
            time.sleep(1)

    def store_tweets(self, tweet):
        try:
            doc_id, doc_rev = self.db.save(tweet)
            print(f"Document stored in database: id: {doc_id}, rev: {doc_rev}")
        except DB.http.ResourceConflict:
            print(f"Document already present in database. Not updated")


def load_sa2_data():
    # read the shape file
    sa2_data = "aust_sa2.geojson"
    sa2_df = gpd.read_file(sa2_data, driver='GeoJson')
    # filter to only include melbourne
    sa2_df = sa2_df[sa2_df['GCC_NAME16'] == 'Greater Melbourne']
    return sa2_df[['SA2_MAIN16', 'geometry']]


# return the SA2 main code for 2016 boundaries
def get_sa2_main16(coordinates, sa2_main16_df):
    if coordinates is None:
        return None

    point = Point([coordinates['longitude'], coordinates['latitude']])

    # check if point falls in the sa2 geometry
    row_filter = sa2_main16_df.apply(lambda row: row['geometry'].contains(point) or row['geometry'].intersects(point),
                                     axis=1)
    filtered_rows = sa2_main16_df[row_filter]
    if (filtered_rows.size == 0):
        return None

    return filtered_rows['SA2_MAIN16'].iloc[0]


def get_tweet_coordinates(tweet_doc):
    """
    Given a tweet doc extract the tweet coordinates
    :param tweet: tweet in JSON format
    :return: dictionary of latitude, longitude
    """
    hasCoordinates = tweet_doc['coordinates']
    if hasCoordinates:
        return {"longitude": hasCoordinates['coordinates'][0], "latitude": hasCoordinates['coordinates'][1]}


if __name__ == '__main__':
    bear_token = INFO.BEAR_TOKEN
    consumer_key = INFO.API_KEY
    consumer_secret = INFO.KEY_SECRET
    access_token = INFO.ACCESS_TOKEN
    access_secret = INFO.TOKEN_SECRET

    t = search(consumer_key, consumer_secret, access_token, access_secret)
    print("Setup complete")
    # coordinates for Melbourne based on a bounding box for the Greater Melbourne region
    coordinates = [144.33363404800002, -38.50298801599996, 145.8784120140001, -37.17509899299995]

    print("Searching tweets...")
    t.search_tweet()
