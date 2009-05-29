import urllib
import xml.dom.minidom
import BeautifulSoup

from twisted.internet import defer, reactor
from twisted.web import client
from twisted.internet.error import DNSLookupError

BASE_URL = "http://api.longurl.org/v1/"

class MyClient:
    def getPageWithLocation(self, url, contextFactory=None, *args, **kwargs):
        factory = client._makeGetterFactory(
                   url,
                   client.HTTPClientFactory,
                   contextFactory=contextFactory,
                   *args, **kwargs)
        return factory.deferred.addCallback(lambda page: (page, factory.url)) \
                               .addErrback(lambda e: e)
    
    def getPage(self, url, contextFactory=None, *args, **kwargs):
        return client._makeGetterFactory(
            url,
            client.HTTPClientFactory,
            contextFactory=contextFactory,
            *args, **kwargs).deferred

class ResponseFailure(Exception):
    pass

class Service(object):
    "An individual service handled by longurl."

    def __init__(self, el):
        self.name = el.getElementsByTagName('name')[0].firstChild.data
        self.domains = []

        for d in el.getElementsByTagName('domain'):
            self.domains.append(d.firstChild.data)

    def __repr__(self):
        return "<Service name=%s, doms=%s>>" % (self.name, str(self.domains))

class Services(dict):
    "List of services handled by longurl"

    def __init__(self, content):
        document=xml.dom.minidom.parseString(content)
        assert document.firstChild.nodeName == "response"
        for r in document.getElementsByTagName('service'):
            s=Service(r)
            self[s.name] = s

class ExpandedURL(object):

    def __init__(self, title, url):
        self.title = title
        self.url = url

    def __repr__(self):
        return "<<ExpandedURL title=%s url=%s>>" % (self.title, self.url)


class LongUrl(object):

    def __init__(self, agent='twisted-longurl', client=MyClient()):
        self.agent = agent
        self.client = client
        
    def getServices(self):
        """Get a dict of known services.

        Key is service name, value is a Service object."""

        rv = defer.Deferred()
        d = self.client.getPage(BASE_URL + 'services', agent=self.agent)
        d.addCallback(lambda res: rv.callback(Services(res)))
        d.addErrback(lambda e: rv.errback(e))

        return rv

    def expand(self, u):
        """Expand a URL."""
        
        def gotResponse(t):
            page, url = t
            soup = BeautifulSoup.BeautifulSoup(page)
            title = soup.title.string
            rv.callback(ExpandedURL(title, url))
        
        rv = defer.Deferred()
        d = self.client.getPageWithLocation(u)
        d.addCallback(gotResponse)
        d.addErrback(lambda e: rv.errback(e))

        return rv
