from copy import deepcopy

from flask import Flask, send_from_directory
from flask_restful import Resource, Api, abort
import couchdb as db
from couchback_temp import CouchInterface

# for data preprocessing
import pandas as pd
from shapely.geometry import Polygon, Point
import geopandas as gpd
import json
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config')

api = Api(app)

analytics = {
    'diversity': {'description': 'Diversity and the federal election'},
    'socioeconomic': {'description': 'Socioeconomic index and the federal election'}
}


def create_couch_interface():
    # initialize a CouchInterface object to retrive data from couchdb
    ci = CouchInterface(address=app.config["COUCHDB_IP"], port=str(app.config["COUCHDB_PORT"]), \
    username=app.config["COUCHDB_USER"], password=app.config["COUCHDB_PASSWORD"])
    return ci


def abort_if_scenario_doesnt_exist(scenario):
    if scenario not in analytics:
        abort(404, message="Scenario {} doesn't exist".format(scenario))


def join_languages_and_polygons(languages, polygons):
    # create df for both query outputs, join them, and export as geojson (here use dict rather than string)
    # preprocess the first query output
    for output in languages:
        # get the initial key-value pair
        sa2 = list(output.keys())[0]
        value = list(output.values())[0]
        prop = None

        if 'Proportion' in value:
            prop = value["Proportion"]
        # re-construct the dict
        output["sa2"] = sa2
        output["prop"] = prop
        del output[sa2]

    # preprocess the second query output
    for output in polygons:
        # get the initial key-value pair
        sa2 = list(output.keys())[0]
        value = list(output.values())[0]
        # re-construct the dict
        try:
            output["sa2"] = str(sa2)
            output["name"] = value['SA2_NAME16']
            rounded_polygon = [list(map(lambda x: round(x, 5), coords)) for coords in value['geometry'][0]]
            output["geometry"] = Polygon(rounded_polygon)
            del output[sa2]
        except(TypeError):
            # some empty geometry? can't get rounded_polygon
            del output[sa2]

    # create dataframes
    languages_df = pd.DataFrame(languages)
    polygons_df = pd.DataFrame(polygons)
    merged_df = languages_df.merge(polygons_df, on="sa2")
    polygon_gdf = gpd.GeoDataFrame(merged_df, geometry=merged_df["geometry"])

    # convert to (geo)json string and then load back to dict
    return json.loads(polygon_gdf.to_json())


def tweets_to_geojson(valid_tweets):
    ## format a list of tweets queried from database to geojson (here use dict rather than string)
    ## get a list of re-structured tweet dict / json object
    tweets = []
    for tweet in valid_tweets:
        value = list(tweet.values())[0]

        # convert tweet timestamp to python datatime
        # e.g. 'Sun Aug 03 08:25:21 +0000 2014' to 2014-08-03 08:25:21
        dtime = value['time']
        new_dtime = datetime.strftime(datetime.strptime(dtime, '%a %b %d %H:%M:%S +0000 %Y'), '%Y-%m-%d %H:%M:%S')

        # convert to a point object
        coord = value['coord']
        coord = Point(coord)

        tweets.append({"compound": value['compound'],
                       "created_at": new_dtime, "text": value['text'], "geometry": coord})

    ## convert to dataframe
    tweets_df = pd.DataFrame(tweets);
    tweets_df.head()
    ## convert to geopandas dataframe
    tweets_gdf = gpd.GeoDataFrame(tweets_df, geometry=tweets_df["geometry"])
    # convert to (geo)json string and then load back to dict
    return json.loads(tweets_gdf.to_json())


def language_proportion_dict(sa2_languages):
    ## Build a dict for language proportion using sa2 code as keys
    ## Convert [{'206011105': {'Proportion': 0.29843663941024445}}, {'206011106': {'Proportion': 0.2914498871110239}}]
    ## To {'206011105': 0.29843663941024445, '206011106': 0.2914498871110239}
    lang_prop_dict = {}
    for output in sa2_languages:
        # get the initial key-value pair
        sa2 = list(output.keys())[0]
        value = list(output.values())[0]
        prop = None

        if 'Proportion' in value:
            prop = value["Proportion"]

        # add to dict
        lang_prop_dict[sa2] = prop
    return lang_prop_dict


# Svelte app
@app.route("/")
def index():
    return send_from_directory('../frontend/public', 'index.html')


# serve static files for the Svelte app
@app.route("/<path:path>")
def home(path):
    return send_from_directory('../frontend/public', path)


# Testing route
@app.route("/api/twitter_database_info/")
def database_status():
    return app.config['TWITTER_DB'].info()


class Analytics(Resource):
    def get(self):
        return analytics


class API(Resource):
    def get(self):
        return [{'resource': 'analytics',
                 'description': 'analytic scenarios exploring liveability in Melbourne',
                 'format': 'json'},
                {'resource': 'twitter_database_info',
                 'description': 'information about the state of the tweet database',
                 'format': 'json'}]


class Diversity(Resource):
    def get(self):
        return [{'resource': 'tweets',
                 'description': 'election themed tweets, including sentiment analysis and SA2 location if coordinates were available',
                 'format': 'geojson'},
                {'resource': 'language',
                 'description': 'polygons of SA2 areas in greater Melbourne with data on diversity based on language spoken',
                 'format': 'geojson'},
                {'resource': 'sentiment',
                 'description': 'election themed tweet sentiment analysis data aggregated by SA2 with diversity data',
                 'format': 'json'}]


class Socioeconomic(Resource):
    def get(self):
        return [{'resource': 'tweets',
                 'description': 'election themed tweets, including sentiment analysis, election issue, and SA2 location if coordinates were available',
                 'format': 'geojson'},
                {'resource': 'language',
                 'description': 'polygons of SA2 areas in greater Melbourne with data on socioeconomic status',
                 'format': 'geojson'},
                {'resource': 'election-issues',
                 'description': 'election themed tweets aggregated by election issue, including mean compound sentiment',
                 'format': 'json'}]


class Tweets(Resource):
    # Return geojson format:
    # { "type": "Feature", “created_at”: xyz,
    #   "properties": { "compound": -0.5362, "text": "#auspol tweets",},
    #   "geometry": { "type": "Point", "coordinates": [ 144.95379890000001, -37.7740309 ] } }
    def get(self):
        # initialize a CouchInterface object to retrieve data from couchdb
        ci = create_couch_interface()

        valid_tweets = ci.non_grouped_results(db_name=app.config["COUCHDB_HISTORIC_DB"], \
        design_doc=app.config["DESIGN_DOC"], view_name=app.config["VIEW_FOR_ELECTION_TWEETS"])
        return tweets_to_geojson(valid_tweets)


class Language(Resource):
    # Return geojson format:
    # { "type": "Feature", "properties": { "SA2_MAIN16": "206011105", "SA2_NAME16": "Brunswick", "prop_spk_other_lang": 0.30813904905155842 },
    #   "geometry": { "type": "Polygon", "coordinates": [ [ [ 144.94974, -37.76277 ], [ 144.95003, -37.76105 ] ] ] } }
    def get(self):
        # initialize a CouchInterface object to retrieve data from couchdb
        ci = create_couch_interface()

        # load language info and polygons of sa2's from database
        sa2_languages = ci.non_grouped_results(db_name=app.config["LSAHBSC"], \
        design_doc=app.config["DESIGN_DOC_AURIN"], view_name=app.config["VIEW_FOR_AURIN"])
        sa2_polygons = ci.non_grouped_results(db_name=app.config["AUSTGEO"], \
        design_doc=app.config["DESIGN_DOC_AURIN"], view_name=app.config["VIEW_FOR_AURIN"])

        # join two outputs, and output a geojson string
        return join_languages_and_polygons(sa2_languages, sa2_polygons)


class Sentiment(Resource):
    # Return a dict (miniature dataframe):
    # {'sa2':sa2s, ‘mean_compound’: list, 'count':counts, ‘prop_spk_other_lang’: list}
    def get(self, scenario_id):
        abort_if_scenario_doesnt_exist(scenario_id)
        # initialize a CouchInterface object to retrieve data from couchdb
        ci = create_couch_interface()
        sa2_languages = ci.non_grouped_results(db_name=app.config["LSAHBSC"], \
        design_doc=app.config["DESIGN_DOC_AURIN"], view_name=app.config["VIEW_FOR_AURIN"])
        lang_prop_dict = language_proportion_dict(sa2_languages)
        scenario = deepcopy(analytics[scenario_id])

        if (scenario_id == "diversity"):

            # get queried results in a list of dict: e.g.
            # {'214021380': {'sum': -1.1561, 'count': 2, 'min': -0.6808, 'max': -0.4753, 'sumsqr': 0.68939873}}
            db_name = app.config["COUCHDB_HISTORIC_DB"]
            design_doc = app.config["DESIGN_DOC"]
            view_name = app.config["VIEW_FOR_ELECTION"]
            results = ci.grouped_results(db_name, design_doc, view_name)

            # convert into a dict of lists (like a dataframe)
            sa2s = []
            avgs = []
            counts = []
            lang_props = []
            for result in results:
                sa2 = list(result.keys())[0]
                sa2s.append(sa2)
                avgs.append(result[sa2]['sum'] / result[sa2]['count'])
                counts.append(result[sa2]['count'])
                lang_props.append(lang_prop_dict[sa2])

            results_zipped = {'sa2': sa2s, 'mean_compound': avgs, 'count': counts, 'prop_spk_other_lang': lang_props}
            scenario['returned_data'] = results_zipped

        return scenario


def tweets_to_geojson_SE(valid_tweets):
    ## to support the socioeconomic scenario
    ## format a list of tweets queried from database to geojson (here use dict rather than string)
    ## get a list of re-structured tweet dict / json object
    tweets = []
    for tweet in valid_tweets:
        key = list(tweet.keys())[0]
        value = list(tweet.values())[0]

        # convert tweet timestamp to python datatime
        # e.g. 'Sun Aug 03 08:25:21 +0000 2014' to 2014-08-03 08:25:21
        dtime = value['time']
        new_dtime = datetime.strftime(datetime.strptime(dtime, '%a %b %d %H:%M:%S +0000 %Y'), '%Y-%m-%d %H:%M:%S')

        # convert to a point object
        coord = value['coord']
        coord = Point(coord)

        tweets.append({"issue": key, "compound": value['compound'],
                       "created_at": new_dtime, "text": value['text'], "geometry": coord})

    ## convert to dataframe
    tweets_df = pd.DataFrame(tweets);
    tweets_df.head()
    ## convert to geopandas dataframe
    tweets_gdf = gpd.GeoDataFrame(tweets_df, geometry=tweets_df["geometry"])
    # convert to (geo)json string and then load back to dict
    return json.loads(tweets_gdf.to_json())


def join_seifa_and_polygons(languages, polygons):
    # create df for both query outputs, join them, and export as geojson (here use dict rather than string)
    # preprocess the first query output
    for output in languages:
        # get the initial key-value pair
        sa2 = list(output.keys())[0]
        value = list(output.values())[0]
        irsad_score = None

        if 'seifa' in value:
            irsad_score = value['seifa']
        # re-construct the dict
        output["sa2"] = sa2
        output["irsad_score"] = irsad_score
        del output[sa2]

    # preprocess the second query output
    for output in polygons:
        # get the initial key-value pair
        sa2 = list(output.keys())[0]
        value = list(output.values())[0]
        # re-construct the dict
        try:
            output["sa2"] = str(sa2)
            output["name"] = value['SA2_NAME16']
            rounded_polygon = [list(map(lambda x: round(x, 5), coords)) for coords in value['geometry'][0]]
            output["geometry"] = Polygon(rounded_polygon)
            del output[sa2]
        except(TypeError):
            # some empty geometry? can't get rounded_polygon
            del output[sa2]

    # create dataframes
    languages_df = pd.DataFrame(languages)
    polygons_df = pd.DataFrame(polygons)
    merged_df = languages_df.merge(polygons_df, on="sa2")
    polygon_gdf = gpd.GeoDataFrame(merged_df, geometry=merged_df["geometry"])

    # convert to (geo)json string and then load back to dict
    return json.loads(polygon_gdf.to_json())


class SE_Tweets(Resource):
    # Return geojson format:
    # { "type": "Feature", “created_at”: xyz, "properties": {
    #   "issue": “childcare”, “compound”: 0.123,
    #   "text": "#auspol tweets, an egghead with my twitter name just followed me? Should I be worried? Weirdness. ..",},
    #   "geometry": { "type": "Point", "coordinates": [ 144.95380, -37.77403 ] } }

    def get(self):
        ci = create_couch_interface()
        valid_tweets = ci.non_grouped_results_singlekey(db_name=app.config["COUCHDB_HISTORIC_DB"], \
        design_doc=app.config["DESIGN_DOC"], view_name=app.config["VIEW_FOR_SOCIAL_TWEETS"])

        return tweets_to_geojson_SE(valid_tweets)


class Seifa(Resource):
    # Return geojson format (using seifa score instead of prop_spk_other_lang):
    # { "type": "Feature", "properties": { "SA2_MAIN16": "206011105", "SA2_NAME16": "Brunswick", "irsad_score":1106},
    #   "geometry": { "type": "Polygon", "coordinates": [ [ [ 144.94974, -37.76277 ], [ 144.95003, -37.76105 ] ] ] } }
    def get(self):
        ci = create_couch_interface()
        # load language info and polygons of sa2's from database
        sa2_seifas = ci.non_grouped_results(db_name=app.config["SEIFA"], \
        design_doc=app.config["DESIGN_DOC_AURIN"], view_name=app.config["VIEW_FOR_AURIN"])
        sa2_polygons = ci.non_grouped_results(db_name=app.config["AUSTGEO"], \
        design_doc=app.config["DESIGN_DOC_AURIN"], view_name=app.config["VIEW_FOR_AURIN"])

        # join two outputs, and output a geojson string
        return join_seifa_and_polygons(sa2_seifas, sa2_polygons)


class Issues_Sentiment(Resource):
    # Return a dict (miniature dataframe):
    # { ‘mean_compound’: list, 'count': list, ‘issue’: list of all the issues}
    def get(self, scenario_id):
        abort_if_scenario_doesnt_exist(scenario_id)
        # initialize a CouchInterface object to retrive data from couchdb
        ci = create_couch_interface()
        scenario = deepcopy(analytics[scenario_id])

        if (scenario_id == "socioeconomic"):
            # get queried results in a list of dict: e.g.
            # {'Aged care': { "sum":-33.6484, "count": 190, "min": -0.8442, "max": 0.6597, "sumsqr": 36.8765}}
            db_name = app.config["COUCHDB_NEW_DB"]
            design_doc = app.config["DESIGN_DOC"]
            view_name = app.config["VIEW_FOR_SOCIAL"]
            results = ci.grouped_results_singlekey(db_name, design_doc, view_name)

            # convert into a dict of lists (like a dataframe)
            avgs = []
            counts = []
            issues = []
            for result in results:
                issue = list(result.keys())[0]
                issues.append(issue)
                avgs.append(result[issue]['sum'] / result[issue]['count'])
                counts.append(result[issue]['count'])

            results_zipped = {'issue': issues, 'mean_compound': avgs, 'count': counts}
            scenario['returned_data'] = results_zipped

        return scenario


# Resources
api.add_resource(API, '/api/')
# general info
api.add_resource(Analytics, '/api/analytics/')
# election scenario
api.add_resource(Diversity, '/api/analytics/diversity/')
api.add_resource(Tweets, '/api/analytics/diversity/tweets/')
api.add_resource(Language, '/api/analytics/diversity/language/')
api.add_resource(Sentiment, '/api/analytics/<string:scenario_id>/sentiment/')
# socioeconomic scenario
api.add_resource(Socioeconomic, '/api/analytics/socioeconomic/')
api.add_resource(SE_Tweets, '/api/analytics/socioeconomic/tweets/')
api.add_resource(Seifa, '/api/analytics/socioeconomic/seifa/')
api.add_resource(Issues_Sentiment, '/api/analytics/<string:scenario_id>/election-issues/')

# connect to database
# couchdb_url = f'http://{app.config["COUCHDB_USER"]}:{app.config["COUCHDB_PASSWORD"]}@{app.config["COUCHDB_IP"]}:{app.config["COUCHDB_PORT"]}/'
# app.logger.info("Connecting to couchDB...")
# couchdb_server = db.Server(couchdb_url)
# app.config['COUCHDB'] = couchdb_server
# app.config['TWITTER_DB'] = couchdb_server[app.config["COUCHDB_TWITTER_DB"]]
# app.logger.debug(app.config['TWITTER_DB'])
# app.logger.info("Connected to couchDB")

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
