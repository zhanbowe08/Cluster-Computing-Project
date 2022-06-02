# Turns on debugging features in Flask
DEBUG = True
# IP address of couchDB
# 172.26.131.244: database-1
# 172.26.134.62: database-2
# 172.26.128.40: database-3
# 172.26.134.153: vm-4
COUCHDB_IP = '172.26.128.40'
# port of couchDB
COUCHDB_PORT = 5984
# username of couchDB
COUCHDB_USER = 'admin'
# password for couchDB
COUCHDB_PASSWORD = 'password'
# database for tweets
COUCHDB_HISTORIC_DB = "twitter_historic"
COUCHDB_NEW_DB = "twitter_new"
# database for aurin
LSAHBSC = "aurin_lsahbsc_sa2"
SEIFA = "aurin_seifa_sa2"
AUSTGEO = "abs_austgeo_sa2"
# design doc name
DESIGN_DOC = "tweets"
DESIGN_DOC_AURIN = "filter"
# view name
VIEW_FOR_ELECTION = "election_sentiment_stats"
VIEW_FOR_SOCIAL = "socioeconomic_sentiment_stats"
VIEW_FOR_ELECTION_TWEETS = "election_tweets"
VIEW_FOR_SOCIAL_TWEETS = "socioeconomic_tweets"
VIEW_FOR_AURIN = "default"
