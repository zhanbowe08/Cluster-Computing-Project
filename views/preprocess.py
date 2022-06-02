from couchback import CouchInterface, MapGenerator
from shapely.geometry import Polygon, MultiPolygon
import pandas as pd


def filter_tweet(couch_itf, database, keywords, design_name='filter', views_name=None, create=True):
    if views_name is None:
        views_name = ['tweets_with_sa2', 'sentiment_per_sa2']

    if create:
        mapreduce_list = []
        mg = MapGenerator()
        mg.add_condition('tweet.text', 'contains', keywords)
        mg.add_condition('sa2', 'exists')
        mg.set_key('tweet.id_str')
        mg.set_value({'sa2': 'sa2', 'compound': 'sentiment.compound', 'text': 'tweet.text',
                      'longitude': 'tweet.coordinates.coordinates[0]', 'latitude': 'tweet.coordinates.coordinates[1]'})
        map_function = mg.generate()
        mapreduce_list.append((map_function,))
        mg.set_key('sa2')
        mg.set_value('sentiment.compound')
        map_function = mg.generate()
        mapreduce_list.append((map_function, '_stats'))
        couch_itf.create_mapreduce_views(database, design_name, mapreduce_list,
                                         views_name=views_name, return_mode=False)
    tweets_with_sa2 = couch_itf.get_view(database, design_name, views_name[0])
    sentiment_per_sa2 = couch_itf.get_view(database, design_name, views_name[1], group_level=1)
    data_tweet = []
    for row in tweets_with_sa2['rows']:
        ins = [row['key'], row['value']['sa2'], row['value']['compound'], row['value']['text'],
               row['value']['longitude'], row['value']['latitude']]
        data_tweet.append(ins)
    data_sentiment = []
    for row in sentiment_per_sa2['rows']:
        ins = [row['key'], row['value']]
        data_sentiment.append(ins)
    tweets_with_sa2_df = pd.DataFrame(data_tweet, columns=['id', 'sa2', 'compound', 'text', 'longitude', 'latitude'])
    sentiment_per_sa2_df = pd.DataFrame(data_sentiment, columns=['sa2', 'stats'])
    return tweets_with_sa2_df, sentiment_per_sa2_df


def get_australia_geo(couch_itf, database='abs_austgeo_sa2', design_name='filter', view_name='default', create=True):
    if create:
        mg = MapGenerator()
        mg.add_condition('GCC_NAME16', 'equals', 'Greater Melbourne')
        mg.set_key({'SA2_MAIN16': 'SA2_MAIN16'})
        mg.set_value({'SA2_NAME16': 'SA2_NAME16', 'geometry': 'coordinates'})
        map_function = mg.generate()
        couch_itf.create_mapreduce_view(database, design_name, map_function, return_mode=False)
    geo_view = couch_itf.get_view(database, design_name, view_name)

    data = []
    for row in geo_view['rows']:
        ins = [row['key']['SA2_MAIN16'], row['value']['SA2_NAME16']]
        geometry = row['value']['geometry']
        if geometry is None:
            ins.append(None)
        elif isinstance(geometry[0][0][0], list):
            polygons = []
            for poly_ins in geometry:
                coordinates = poly_ins[0]
                plg = Polygon(coordinates)
                polygons.append(plg)
            multi = MultiPolygon(polygons)
            ins.append(multi)
        else:
            poly = Polygon(geometry[0])
            ins.append(poly)
        data.append(ins)
    df = pd.DataFrame(data, columns=['SA2_MAIN16', 'SA2_NAME16', 'geometry'])
    return df


def get_lang_diversity(couch_itf, database='aurin_lsahbsc_sa2', design_name='filter', view_name='default', create=True):
    if create:
        mg = MapGenerator()
        mg.set_key('sa2_main16')
        mg.set_value(['os_visitors_p', 'lang_spoken_home_ns_p', 'spks_other_lang_tot_p', 'spks_eng_on_p', 'tot_p'])
        map_function = mg.generate()
        couch_itf.create_mapreduce_view(database, design_name, map_function, return_mode=False)
    lang_view = couch_itf.get_view(database, design_name, view_name)
    data_lang = []
    for row in lang_view['rows']:
        ins = [row['key'], row['value'][0], row['value'][1], row['value'][2], row['value'][3], row['value'][4]]
        data_lang.append(ins)
    lang_df = pd.DataFrame(data_lang, columns=['sa2', 'visitors', 'not_stated', 'other_lang', 'english_only', 'total'])
    return lang_df


def get_social_economy(couch_itf, database='aurin_seifa_sa2', design_name='filter', view_name='default', create=True):
    if create:
        mg = MapGenerator()
        mg.set_key('sa2_main16')
        mg.set_value('irsad_score')
        map_function = mg.generate()
        couch_itf.create_mapreduce_view(database, design_name, map_function, return_mode=False)
    se_view = couch_itf.get_view(database, design_name, view_name)
    data_se = []
    for row in se_view['rows']:
        ins = [row['key'], row['value']]
        data_se.append(ins)
    se_df = pd.DataFrame(data_se, columns=['sa2', 'irsad'])
    return se_df


if __name__ == '__main__':
    USERNAME = 'admin'
    PASSWORD = 'password'
    ADDRESS = '172.26.134.62'
    PORT = '5984'
    KEYWORDS = ['scott morrison', 'scomo', 'prime minister', 'scummo', 'scumo', 'scotty from marketing', '#auspol',
                '#ausvotes', '#ausvotes2022', '#ausvotes22', '#scottyfrommarketing', '#ScottyFromPhotoOps',
                '#ScottyTheGaslighter', '#ScottyThePathologicalLiar', '@ScottMorrisonMP']

    ci = CouchInterface(address=ADDRESS, port=PORT, username=USERNAME, password=PASSWORD)

    tweets_his, sent_p_sa2_his = filter_tweet(ci, 'twitter_historic', KEYWORDS, design_name='filter', create=False)
    # tweets_new, sent_p_sa2_new = filter_tweet(ci, 'twitter_new', KEYWORDS, design_name='filter')
    sa2_geometry = get_australia_geo(ci, create=False)
    lang_diversity = get_lang_diversity(ci, create=False)
    social_economy = get_social_economy(ci, create=False)
    print('end')
