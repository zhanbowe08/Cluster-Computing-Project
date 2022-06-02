import couchdb
import json
import requests
import pandas as pd


class CouchInterface:
    def __init__(self, address='172.26.131.244', port='5984', username='admin', password='password'):
        self.username = username
        self.password = password
        self.address = address
        self.port = port
        self.url = 'http://' + self.username + ':' + self.password + '@' + self.address + ':' + self.port + '/'
        self.server = couchdb.Server(self.url)

    def _create_design(self, database: str, design_name: str):
        db = self.server[database]
        design_doc = {'_id': '_design/' + design_name}
        db.save(design_doc)

    def _delete_design(self, database: str, design_name: str):
        db = self.server[database]
        design_id = '_design/' + design_name
        design_doc = db[design_id]
        db.delete(design_doc)

    def get_view(self, database: str, design_name: str, view_name: str):
        """
        If you have created a view and just want to get it again, it is not necessary to invoke create_regex_view, you
        can just call this method.

        :param database: the name of specific database
        :param design_name: the name of design document
        :param view_name: the name of view you want
        :return:
        """
        resp = requests.get(self.url + database + '/_design/' + design_name + '/_view/' + view_name)
        view = json.loads(resp.text)
        return view

    def create_regex_view(self, database: str, field: str, regex: str, design_name: str, view_name: str = 'default'):
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
        design_name = '_design/' + design_name
        map_fun = 'function (doc) { var reg = ' + regex + '; ' \
            'if (reg.test(doc.' + field + ')) { emit(doc.' + field + ', doc._id); } }'
        data = {'views': {view_name: {'map': map_fun}}}
        requests.put(self.url + database + '/' + design_name, data=json.dumps(data))
        resp = requests.get(self.url + database + '/' + design_name + '/_view/' + view_name)
        view = json.loads(resp.text)
        return view

    def create_regex_views(self, database: str, fields: list, regexes: list, design_name: str, views_name: list):
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
        design_name = '_design/' + design_name
        data = {'views': {}}
        for i, view_name in enumerate(views_name):
            # map_fun = 'function (doc) { var reg = ' + regexes[i] + '; ' \
            #     'if (reg.test(doc.' + fields[i] + ')) { emit(doc.' + \
            #           fields[i] + ', doc._id); } }'
            map_fun = 'function (doc) { var reg = ' + regexes[i] + '; ' \
                'if (reg.test(doc.' + fields[i] + ')) { emit(' + '"' + regexes[i][1:-2] + '"' + ', doc._id); } }'
            data['views'][view_name] = {'map': map_fun}
        requests.put(self.url + database + '/' + design_name, data=json.dumps(data))
        views = []
        for view_name in views_name:
            resp = requests.get(self.url + database + '/' + design_name + '/_view/' + view_name)
            view = json.loads(resp.text)
            views.append(view)
        return views

    def create_regex_view_combined(self, database: str, field: str, regexes: list, design_name: str, view_name: str="election_tweets"):
        """
        Similar with create_regex_view, and create_regex_views. However, we search tweets using all regex words in a single view.
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

    def grouped_results(self, db_name, design_doc, view_name):
        """
        a database has a design document and view under the path /db_name/_design/design_doc/_view/view_name
        """
        db = self.server[db_name]
        path = design_doc + '/' + view_name
        results = []
        for item in db.view(path, group=True):
            results.append({item.key[1] : item.value})

        return results

    def grouped_results_singlekey(self, db_name, design_doc, view_name):
        # key is no longer a list of two elements as before
        db = self.server[db_name]
        path = design_doc + '/' + view_name
        results = []
        for item in db.view(path, group=True):
            results.append({item.key : item.value})

        return results

    def non_grouped_results(self, db_name, design_doc, view_name):
        """
        a database has a design document and view under the path /db_name/_design/design_doc/_view/view_name
        """
        db = self.server[db_name]
        path = design_doc + '/' + view_name
        results = []
        for item in db.view(path):
            results.append({item.key[1] : item.value})

        return results

    def non_grouped_results_singlekey(self, db_name, design_doc, view_name):
        # key is no longer a list of two elements as before
        db = self.server[db_name]
        path = design_doc + '/' + view_name
        results = []
        for item in db.view(path):
            results.append({item.key : item.value})

        return results


if __name__ == '__main__':
    # ci = CouchInterface(address='localhost', port='5984', username='admin', password='password')
    # ret = ci.create_regex_view('twitter_new', 'tweet.text', '/melbourne/i', 'test1')

    # the keywords to filter out
    election_keywords = ['/auspol/i', '/ausvotes/i', '/ausvotes2022/i', '/ausvotes22/i',
    '/ScottMorrison/i', '/Scott/i', '/Morrison/i', '/ScottMorrisonMP/i', '/election/i']

    ci = CouchInterface(address='172.26.131.244', port='5984', username='admin', password='password')

    if("error" in ci.get_view("twitter_historic", "tweets", "election_tweets")): # if view not exist
        # create a new view
        ret = ci.create_regex_view_combined('twitter_historic', 'doc.tweet', election_keywords, 'tweets', 'election_tweets')

    # receiving a grouping result from the view
    results = ci.grouping_results("twitter_historic", "tweets", "election_tweets")
    print(results)

    print('test case ends.')
