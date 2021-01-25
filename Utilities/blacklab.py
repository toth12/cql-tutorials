"""Functions to use the BlackLab server."""

try:
    from urllib.request import urlopen
    from urllib.parse import quote, quote_plus
except ImportError:
    from urllib2 import urlopen
    from urllib import quote
import json
import sys; sys.path.insert(0, '..')
import constants
from gensim.models.phrases import Phrases, Phraser
import pdb



def search_blacklab(query, window=5, document_id=None,
                    lemma=False, include_match=True,
                    search_terms=None,left = True, right = True):
    """Run a search against the blacklab server.

    For full documentatio on these parameters, see the official BlackLab
    documentation:
    http://inl.github.io/BlackLab/blacklab-server-overview.html

    Parameters
    ----------
    query : {str}
        A valid CQL query.
    window : {number}, optional
        Window of words to be included after the query (the default is 5)
    document_id : {str}, optional
        If document id is present,only the document with id is queried
        (the default is None)
    lemma : {bool}, optional
        If true lemmas are returned and not words (the default is False)
    include_match : {bool}, optional
        If false, match is excluded and only surrounding words are returned
        . If include is false, window is to be more than 0(the default is True)
    search_terms : {[type]}, optional
        [description] (the default is None, which [default_description])

    Returns
    -------
    list
        List of dictionaries that are search results. Each list consists
        of 'left' and 'right' that are the context words surrounding the
        result. It also contains 'match_word' that are the original words
        retrieved. "complete_match" contains the lemmas that are retrieved.
        If lemmas False, 'complete_match' and 'match_word' are the same. Other
        elements of the dictionary:  'testimony_id', 'shelfmark',
        'token_start', 'token_end'.
    """
    params = []
    root = constants.BLACKLAB_URL + 'hits'
    # query-based arguments
    arguments = {
        # 'first': '0',
        # 'limit':'100',
        'patt': quote_plus(query),
        'waitfortotal': 'true',
        'outputformat': 'json',
        'prettyprint': 'no',
        'wordsaroundhit': window,
    }
    if document_id is not None:
        arguments['filter'] = quote_plus('testimony_id:"' + document_id + '"')
    # compose url for blacklab query
    query = root + '?'
    for idx, arg in enumerate(arguments):
        if idx > 0:
            query += '&'
        query += arg + '=' + str(arguments[arg])

    # add filter params
    filter_join = '%20AND%20'
    non_filter_fields = ['start', 'limit', 'query', 'min_year', 'max_year']
    filter_params = [i for i in params if i not in non_filter_fields]
    if filter_params:
        query += '&filter='
        for i in filter_params:
            query += i + ':' + quote('"' + str(params[i]) + '"') + filter_join
        query = filter_join.join(query.split(filter_join)[:-1])
        query += add_year_params(params, filter_join)
    else:
        query += add_year_params(params, '&filter=')

    '''first find the total number of results available \
      (number set to zero so that nothing is actually
      returned just the number of docs)
    '''

    result = request_url(query + '&number=0')
    total = get_total_numbers(result)
    i = 0
    final_result = []
    for i in range(0, total, 20):
        result = request_url(query + '&first=' + str(i) + '&limit=1')
        result = parse_response(result, include_match=include_match,
                                lemma=lemma, search_terms=search_terms,add_left=left,add_right=right)
        final_result    .extend(result['results'])
    return final_result


def get_query_pattern(query):
    """Curate a search query from a user-provided query expression.

    Parameters
    ----------
    query : {str}
        The raw, user-provided query.
    Returns
    -------
    str
        The user's query in curated form.
    """
    query = query.strip()
    strip_chars = '“”"\''
    for i in strip_chars:
        query = query.strip(i)
    parens = ['[', ']', '(', ')']
    # case of CQL query
    if (query) and (query[0] in parens) and (query[-1] in parens):
        return query
    # case of multiword query
    elif ' ' in query:
        formatted = ''
        for i in query.split():
            formatted += '[word="' + i + '"]'
        return formatted
    # case of simple query
    return '"' + query + '"'


def add_year_params(params, prefix):
    """Limit the year range of matches.

    Given a url param dict, return a string that limits the
    year range of matches if the user passed min_year and
    max_year values.

    Parameters
    ----------
    params : {dict}
        The paramters passed through the url to the search endpoint.
    prefix : {dict}
        A prefix to prepend to the returned query params (if relevant).
    Returns
    -------
    string
        A string with the year query params encoded (if applicable).
    """
    if ('min_year' not in params) or ('max_year' not in params):
        return ''
    param = ''
    param += prefix + 'recording_year:'
    param += '%5B' + params['min_year'] + '%20' + params['max_year'] + '%5D'
    return param


def request_url(url):
    '''
    Request the JSON content at a given url
    @arsg:
        {str} url: the url whose content should be fetched
    @returns:
        {obj} an object with the JSON served at `url`
    '''
    #print(' * requesting', url)
    json_response = urlopen(url).read().decode('utf8')
    return json.loads(json_response)


def parse_response(obj,lemma, include_match = True, search_terms = None,add_left = True, add_right = True):
    '''
        Parse a BlackLab server response object into the required format
        @args:
            {obj} a response from a BlackLab server query
        @returns:
            {obj} an object in the format required by the client
    '''
    total = obj['summary']['numberOfHitsRetrieved']
    doc_infos = obj['docInfos']
    results = []
    for h in obj['hits']:
        
        if add_left == True:
            left = get_match_string(h['left'],search_terms = search_terms, lemma = lemma)
            left_original = get_match_string(h['left'],search_terms = search_terms)
        else:
            left =''
            left_original = ''
        if add_right == True:
            right = get_match_string(h['right'],search_terms = search_terms, lemma = lemma )
            right_original = get_match_string(h['right'],search_terms = search_terms)
        else:
            right = ''
            right_original = ''
        
        match = get_match_string(h['match'],search_terms = search_terms, lemma = lemma)
        match_original = get_match_string(h['match'],search_terms = search_terms)

        complete_match=left+match+right
        complete_match_word = left_original+match_original+right_original
        
        if include_match:
            results.append({
                'left': left,
                'match_word' : complete_match_word,
                'right': right,
                'complete_match':complete_match,
                'testimony_id': get_testimony_meta(h, 'testimony_id', doc_infos),
                'shelfmark': get_testimony_meta(h, 'shelfmark', doc_infos),
                'token_start': h['start'],
                'token_end': h['end']
                })
        else:
            results.append({
                                'left': left,
                                'right': right,
                                'match_word' : complete_match_word  ,
                                'complete_match':left + right,
                                'testimony_id': get_testimony_meta(h, 'testimony_id', doc_infos),
                                'shelfmark': get_testimony_meta(h, 'shelfmark', doc_infos),
                                'token_start': h['start'],
                                'token_end': h['end']
                            })
    return {
        'total': total,
        'results': results,
    }


def parse_response_query_snippets(obj,lemma):
    '''
    Parse a BlackLab server response object into the required format
    @args:
    {obj} a response from a BlackLab server query
    @returns:
    {obj} an object in the format required by the client
    '''
    total = obj['summary']['numberOfHitsRetrieved']
    results = []
    for h in obj['docs']:
            for f in h['snippets']:
                left = get_match_string(f['left'],lemma)
                right = get_match_string(f['right'],lemma)
                match = get_match_string(f['match'],lemma)
                results.append(left+match+right)
        
    return {
        'total': total,
        'results': results,
    }


def get_total_numbers(obj):
    '''
    Parse a BlackLab server response and returns how many hits are available
    @args:
        {obj} a response from a BlackLab server query
    @returns:
        {obj} number of hits
    '''
    total = obj['summary']['numberOfHitsRetrieved']
    return total


def get_match_string(obj,lemma=False,search_terms=None,pos_filter = True):
    '''
    Parse an object with keys `punct` and `word` which indicates
    the word and punctuation that need to occur in sequence to
    reassemble a BlackLab input string
    @args:
        {obj} obj: either hits[i]['left'] or hits[i]['right']
    @returns:
        {str} the string contained in the given side of the hit
    '''
    
    match_string = ''
    if lemma ==False:
        for idx, i in enumerate(obj['word']):
            match_string += i + obj['punct'][idx]
    
    else:
        
        #this is added here
        if pos_filter:
            indices = []
            for c,element in enumerate(obj['pos']):
                if (element[0] == "V") or (element[0] == "N"):
                    indices.append(c)
            for idx, i in enumerate(obj['lemma']):
                if idx in indices:
                    match_string += i + obj['punct'][idx]
        

        else:
            
            for idx, i in enumerate(obj['lemma']):
                match_string += i + obj['punct'][idx]



    if search_terms is not None:
        for search_term in search_terms:
            match_string = match_string.replace(search_term,'')
    
    return match_string


def get_testimony_meta(obj, field, doc_infos):
    '''
    Return the `field` attribute for a hit object in a BlackLab query response
    @args:
        {obj} obj: a BlackLab hit object
        {str} field: the metadata field to return
        {obj} doc_infos: an object with all hit metadata
    @returns:
        {str} the `field` metadata attribute for this hit
    '''
    return doc_infos[obj['docPid']][field]


class iterable_results(object):
    def __init__(self, search_pattern, window=5,lemma=False,document_ids=None,path_to_phrase_model=None):
        self.ids = document_ids
        search_blacklabf.window = window
        self.search_pattern = search_pattern
        self.lemma = lemma
        self.path_to_phrase_model = path_to_phrase_model
        if path_to_phrase_model is not None:
            self.phraser_model = Phraser(Phrases.load(path_to_phrase_model))
        
        

 
    def __iter__(self):
        if self.ids is not None:
            for index,i in enumerate(self.ids):
                results=search_blacklab(self.search_pattern,document_id=i,window=self.window,lemma=self.lemma)
                for result in results:
                    if self.path_to_phrase_model is not None:
                        yield  self.phraser_model[result['complete_match'].strip().split(' ')]
                    else:
                        yield result['complete_match'].strip().split(' ')
        else:
                results=search_blacklab(self.search_pattern,document_id=None,window=self.window,lemma=self.lemma)
                for result in results:
                    if self.path_to_phrase_model is not None:
                        yield  self.phraser_model[result['complete_match'].strip().split(' ')]
                    else:
                        yield result['complete_match'].strip().split(' ')


def main():
    response = search_blacklab('<s/> (<s/> containing ["\["] []{0,5} [lemma="cry"]  []{0,5} ["\]"]) <s/>',window=0,lemma=True)
    pdb.set_trace()
    print(len(response))
if __name__ == '__main__':
        main()    