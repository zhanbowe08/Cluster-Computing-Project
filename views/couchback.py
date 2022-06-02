from typing import Any, Optional, Union
import couchdb
import json
import requests


class CouchInterface:
    def __init__(self, address='172.26.131.244', port='5984', username='admin', password='password'):
        self.username = username
        self.password = password
        self.address = address
        self.port = port
        self.url = 'http://' + self.username + ':' + self.password + '@' + self.address + ':' + self.port + '/'
        self.server = couchdb.Server(self.url)

    def _create_design(self, database: str, design_name: str) -> None:
        db = self.server[database]
        design_doc = {'_id': '_design/' + design_name}
        db.save(design_doc)

    def _delete_design(self, database: str, design_name: str) -> None:
        db = self.server[database]
        design_id = '_design/' + design_name
        design_doc = db[design_id]
        db.delete(design_doc)

    def _create_view(self, database: str, design_name: str, data: str,
                     view_name: str, return_mode: bool = True) -> Optional[dict]:
        design_name = '_design/' + design_name
        requests.put(self.url + database + '/' + design_name, data=data)
        if return_mode:
            resp = requests.get(self.url + database + '/' + design_name + '/_view/' + view_name)
            view = json.loads(resp.text)
            return view

    def _create_views(self, database: str, design_name: str, data: str,
                      views_name: list, return_mode: bool = True) -> Optional[list]:
        design_name = '_design/' + design_name
        requests.put(self.url + database + '/' + design_name, data=data)
        if return_mode:
            views = []
            for view_name in views_name:
                resp = requests.get(self.url + database + '/' + design_name + '/_view/' + view_name)
                view = json.loads(resp.text)
                views.append(view)
            return views

    def get_view(self, database: str, design_name: str, view_name: str, group_level: int = None) -> dict:
        """
        If you have created a view and just want to get it again, it is not necessary to invoke create_regex_view, you
        can just call this method.

        :param database: the name of specific database
        :param design_name: the name of design document
        :param view_name: the name of view you want
        :param group_level: can be a number n, which means the n_th key field to group by
        :return: a dictionary of view
        """
        design_name = '_design/' + design_name
        if group_level:
            query = '?group_level=' + str(group_level)
        else:
            query = ''
        resp = requests.get(self.url + database + '/' + design_name + '/_view/' + view_name + query)
        view = json.loads(resp.text)
        return view

    def create_regex_view(self, database: str, field: str, regex: str,
                          design_name: str, view_name: str = 'default') -> dict:
        """
        This method creates a new design document, and creates a view whose curtain field satisfying the regex given.
        Note: A design_name can only be used once. If you specify an existing design_name for another regex rule, it
        will not be overwritten. If you do want to overwrite a design document, please delete the older one first.

        :param database: the name of specific database
        :param field: if you want to specify a member of a field, please use '.' to separate them.
        :param regex: a javascript regex, like '/melbourne/i'
        :param design_name: you must specify a name of new design document
        :param view_name: [optional] default is 'default'
        :return: the view object created
        """
        map_fun = 'function (doc) { var reg = ' + regex + '; ' \
            'if (reg.test(doc.' + field + ')) { emit(doc.' + field + ', doc); } }'
        data = {'views': {view_name: {'map': map_fun}}}
        data_str = json.dumps(data)
        return self._create_view(database, design_name, data_str, view_name)

    def create_regex_views(self, database: str, fields: list, regexes: list,
                           design_name: str, views_name: list) -> list:
        """
        Similar with create_regex_view, but the difference is this method can simultaneously create multiple views.
        Note: The fields, regexes, and views_name parameters are lists with exactly SAME LENGTH.

        :param database: the name of specific database
        :param fields: the list containing fields you want to filter
        :param regexes: the list containing corresponding rule
        :param design_name: you must specify a name of new design document
        :param views_name: the list of views' name you create
        :return: a list of views
        """
        assert len(fields) == len(regexes) == len(views_name)
        data = {'views': {}}
        for i, view_name in enumerate(views_name):
            map_fun = 'function (doc) { var reg = ' + regexes[i] + '; ' \
                'if (reg.test(doc.' + fields[i] + ')) { emit(doc.' + \
                      fields[i] + ', doc); } }'
            data['views'][view_name] = {'map': map_fun}
        data_str = json.dumps(data)
        return self._create_views(database, design_name, data_str, views_name)

    def create_mapreduce_view(self, database: str, design_name: str, map_fun: str, reduce_fun: str = None,
                              view_name: str = 'default', return_mode: bool = True) -> Optional[dict]:
        """
        Create a view according to the provided map function and reduce function. The both functions must be in string
        format.

        :param database: the name of specific database
        :param design_name: You must specify a name of new design document.
        :param map_fun: A map function must be provided, which can be generated by a MapGenerator.
        :param reduce_fun: [optional] If it is None, no reduce will be applied on the view.
        :param view_name: [optional] default is 'default'
        :param return_mode: determine whether to get the view back
        :return: the view created
        """
        if reduce_fun:
            data = {'views': {view_name: {'map': map_fun, 'reduce': reduce_fun}}}
        else:
            data = {'views': {view_name: {'map': map_fun}}}
        data_str = json.dumps(data)
        return self._create_view(database, design_name, data_str, view_name, return_mode=return_mode)

    def create_mapreduce_views(self, database: str, design_name: str, mapreduce_funcs: list,
                               views_name: list, return_mode: bool = True) -> Optional[list]:
        """
        Similar with create_mapreduce_view, but it can create more views at a time. The mapreduce_funcs refers to a list
        of map-reduce-pair. A map-reduce-pair here can be a list or tuple of one or two string of javascript functions.
        The length of mapreduce_funcs and views_name must be same.

        :param database: the name of specific database
        :param design_name: You must specify a name of new design document.
        :param mapreduce_funcs: a list of list or a list of tuple
        :param views_name: corresponding name of each view
        :param return_mode: determine whether to get the view back
        :return: a list of view dictionary
        """
        assert len(mapreduce_funcs) == len(views_name)
        data = {'views': {}}
        for i, func_pair in enumerate(mapreduce_funcs):
            if len(func_pair) == 1:
                data['views'][views_name[i]] = {'map': func_pair[0]}
            elif len(func_pair) == 2:
                data['views'][views_name[i]] = {'map': func_pair[0], 'reduce': func_pair[1]}
            else:
                e = RuntimeError('The element of mapreduce_funcs should be a list of one or two string of functions.')
                raise e
        data_str = json.dumps(data)
        return self._create_views(database, design_name, data_str, views_name, return_mode=return_mode)

    def create_regex_view_combined(self, database: str, field: str, regexes: list, design_name: str,
                                   view_name: str = "election_tweets"):
        """
        Similar with create_regex_view, and create_regex_views. However, we search tweets using all regex words in a
        single view.
        """

        design_name = '_design/' + design_name

        regs_str = "["
        for i, reg in enumerate(regexes):
            regs_str += reg
            regs_str += ","
        regs_str = regs_str[:-1]
        regs_str += "]"

        map_fun = 'function (doc) {' + \
                  'var regs = ' + regs_str + '; ' + \
                  'var to_emit = false;' + \
                  'if (' + field + '.coordinates){' + \
                  'for (var i in regs) {' + \
                  'if (regs[i].test(' + field + '.text)){' + \
                  'to_emit = true;' + \
                  '}' + \
                  '}' + \
                  'if (to_emit && doc.sa2 && doc.sentiment.compound){' + \
                  'emit(["election",doc.sa2], doc.sentiment.compound);' + \
                  '}' + \
                  '}' + \
                  '}'

        data = {'views': {view_name: {'map': map_fun}}}

        print(requests.put(self.url + database + '/' + design_name, data=json.dumps(data)).json())
        resp = requests.get(self.url + database + '/' + design_name + '/_view/' + view_name)
        view = json.loads(resp.text)
        return view

    def grouping_results(self, db_name, design_doc, view_name):
        """
        a database has a design document and view under the path /db_name/_design/design_doc/_view/view_name
        """
        db = self.server[db_name]
        path = design_doc + '/' + view_name
        results = []
        for item in db.view(path, group=True):
            results.append((item.key, item.value))

        return results


class MapGenerator:
    def __init__(self):
        self.conditions = []
        self.key = 'doc._id'
        self.value = 'doc'

    def add_condition(self, field: str, operator: str, value: Any = None) -> None:
        """
        You can add a condition to filter the data, this condition will be automatically added into the final string
        generated by this MapGenerator. The operator 'equals' is used to filter the data with specific 'field' equals
        (==) the value provided. The 'satisfies' can be used along with a regular expression. The 'contains' requires
        the specific field contains at least one element in a list 'value'. The 'exists' needs no value, which only
        checks whether this field exists and does not equal to null.

        :param field: the field you want to apply the rule
        :param operator: the rule operator, can be 'equals', 'satisfies', 'contains', 'exists'
        :param value: the corresponding value needed by the operator
        :return: None
        """
        if operator == 'equals' and value:
            if isinstance(value, str):
                value = f'"{value}"'
            else:
                value = str(value)
            condition = f'doc.{field} == {value}'
            self.conditions.append(condition)
        elif operator == 'satisfies' and value:
            condition = f'{value}.test(doc.{field})'
            self.conditions.append(condition)
        elif operator == 'contains' and value:
            regex = f'/({"|".join(value)})/i'
            condition = f'{regex}.test(doc.{field})'
            self.conditions.append(condition)
        elif operator == 'exists':
            condition = f'doc.{field}'
            self.conditions.append(condition)

    def set_key(self, keys: Union[str, list, dict]) -> None:
        """
        You can input a str or a list of string to set as keys you want to see in the final view.

        :param keys: a str or a list of string, which usually exist in the data
        :return: None
        """
        if isinstance(keys, str):
            self.key = f'doc.{keys}'
        elif isinstance(keys, list):
            self.key = f'[{", ".join(["doc." + key for key in keys])}]'
        elif isinstance(keys, dict):
            self.key = '{' + ', '.join(['"' + k + '": doc.' + v for k, v in keys.items()]) + '}'
        else:
            e = RuntimeError('The keys must be a string or a list of string!')
            raise e

    def set_value(self, values: Union[str, list, dict]) -> None:
        """
        You can input a str or a list of string to set as keys you want to see in the final view. Note that if you
        specify more than one value, it would be better that these values are numeric. Otherwise, the reduce function
        may not work as you imagine.

        :param values: a str or a list of string, which usually exist in the data
        :return: None
        """
        if isinstance(values, str):
            self.value = f'doc.{values}'
        elif isinstance(values, list):
            self.value = f'[{", ".join(["doc." + value for value in values])}]'
        elif isinstance(values, dict):
            self.value = '{' + ', '.join(['"' + k + '": doc.' + v for k, v in values.items()]) + '}'
        else:
            e = RuntimeError('The values must be a string or a list of string!')
            raise e

    def generate(self) -> str:
        """
        Generate the map function you need according to what you have input into this MapGenerator object.

        :return: a string of the function you describe
        """
        if len(self.conditions) == 0:
            map_fun = 'function (doc) { emit(' + self.key + ', ' + self.value + ') }'
        else:
            conditions = ' && '.join(self.conditions)
            map_fun = 'function (doc) { if (' + conditions + ') { emit(' + self.key + ', ' + self.value + ') } }'
        return map_fun


def test_historic_election_tweet():
    """
    This is just a test case. You can run your own test cases here.
    :return:
    """
    # the keywords to filter out
    election_keywords = ['/auspol/i', '/ausvotes/i', '/ausvotes2022/i', '/ausvotes22/i',
                         '/ScottMorrison/i', '/Scott/i', '/Morrison/i', '/ScottMorrisonMP/i', '/election/i']

    if "error" in ci.get_view("twitter_historic", "tweets", "election_tweets"):  # if view not exist
        # create a new view
        ret_view = ci.create_regex_view_combined('twitter_historic', 'doc.tweet', election_keywords, 'tweets',
                                                 'election_tweets')
        print(ret_view)

    # receiving a grouping result from the view
    results = ci.grouping_results("twitter_historic", "tweets", "election_tweets")
    print(results)


if __name__ == '__main__':
    ci = CouchInterface(address='172.26.131.244', port='5984', username='admin', password='password')

    # ret = ci.create_regex_view('twitter_new', 'tweet.text', '/melbourne/i', 'test1')

    # ret = ci.create_regex_views('twitter_new',
    #                             ['tweet.text', 'tweet.text'],
    #                             ['/melbourne/i', '/vote/i'],
    #                             'test2',
    #                             ['filter_mel', 'filter_vote']
    #                             )

    # test_historic_election_tweet()

    mg = MapGenerator()
    mg.add_condition('tweet.text', 'contains', ['election', 'morrison', 'melbourne'])
    mg.add_condition('sa2', 'exists')
    mg.set_key('sa2')
    mg.set_value('sentiment.compound')
    map_function = mg.generate()
    # ret_ori = ci.create_mapreduce_view('twitter_historic', 'test0', map_function, '_stats')
    ret = ci.get_view('twitter_historic', 'test0', 'default', 1)
    print('test case ends.')
