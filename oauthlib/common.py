# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

"""
oauthlib.common
~~~~~~~~~~~~~~

This module provides data structures and utilities common
to all implementations of OAuth.
"""

import random
import re
import sys
import time
try:
    from urllib import quote as _quote
    from urllib import unquote as _unquote
    from urllib import urlencode as _urlencode
except ImportError:
    from urllib.parse import quote as _quote
    from urllib.parse import unquote as _unquote
    from urllib.parse import urlencode as _urlencode
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

UNICODE_ASCII_CHARACTER_SET = ('abcdefghijklmnopqrstuvwxyz'
                               'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                               '0123456789')

always_safe = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789' '_.-')

PY3 = sys.version_info[0] == 3


if PY3:
    unicode_type = str
    bytes_type = bytes
else:
    unicode_type = unicode
    bytes_type = str


# 'safe' must be bytes (Python 2.6 requires bytes, other versions allow either)
def quote(s, safe=b'/'):
    s = s.encode('utf-8') if isinstance(s, unicode_type) else s
    s = _quote(s, safe)
    # PY3 always returns unicode.  PY2 may return either, depending on whether
    # it had to modify the string.
    if isinstance(s, bytes_type):
        s = s.decode('utf-8')
    return s


def unquote(s):
    s = _unquote(s)
    # PY3 always returns unicode.  PY2 seems to always return what you give it,
    # which differs from quote's behavior.  Just to be safe, make sure it is
    # unicode before we return.
    if isinstance(s, bytes_type):
        s = s.decode('utf-8')
    return s


def urlencode(params):
    utf8_params = encode_params_utf8(params)
    urlencoded = _urlencode(utf8_params)
    if isinstance(urlencoded, unicode_type):  # PY3 returns unicode
        return urlencoded
    else:
        return urlencoded.decode("utf-8")


def encode_params_utf8(params):
    """Ensures that all parameters in a list of 2-element tuples are encoded to
    bytestrings using UTF-8
    """
    encoded = []
    for k, v in params:
        encoded.append((
            k.encode('utf-8') if isinstance(k, unicode_type) else k,
            v.encode('utf-8') if isinstance(v, unicode_type) else v))
    return encoded


def decode_params_utf8(params):
    """Ensures that all parameters in a list of 2-element tuples are decoded to
    unicode using UTF-8.
    """
    decoded = []
    for k, v in params:
        decoded.append((
            k.decode('utf-8') if isinstance(k, bytes_type) else k,
            v.decode('utf-8') if isinstance(v, bytes_type) else v))
    return decoded


urlencoded = set(always_safe) | set('=&;%+~')


def urldecode(query):
    """Decode a query string in x-www-form-urlencoded format into a sequence
    of two-element tuples.

    Unlike urlparse.parse_qsl(..., strict_parsing=True) urldecode will enforce
    correct formatting of the query string by validation. If validation fails
    a ValueError will be raised. urllib.parse_qsl will only raise errors if
    any of name-value pairs omits the equals sign.
    """
    # Check if query contains invalid characters
    if query and not set(query) <= urlencoded:
        raise ValueError('Not a valid urlencoded string.')

    # Check for correctly hex encoded values using a regular expression
    # All encoded values begin with % followed by two hex characters
    # correct = %00, %A0, %0A, %FF
    # invalid = %G0, %5H, %PO
    invalid_hex = '%[^0-9A-Fa-f]|%[0-9A-Fa-f][^0-9A-Fa-f]'
    if len(re.findall(invalid_hex, query)):
        raise ValueError('Invalid hex encoding in query string.')

    query = query.encode('utf-8') if isinstance(query, unicode_type) else query
    # We want to allow queries such as "c2" whereas urlparse.parse_qsl
    # with the strict_parsing flag will not.
    params = urlparse.parse_qsl(query, keep_blank_values=True)

    # unicode all the things
    return decode_params_utf8(params)


def extract_params(raw):
    """Extract parameters and return them as a list of 2-tuples.

    Will successfully extract parameters from urlencoded query strings,
    dicts, or lists of 2-tuples. Empty strings/dicts/lists will return an
    empty list of parameters. Any other input will result in a return
    value of None.
    """
    if isinstance(raw, bytes_type) or isinstance(raw, unicode_type):
        try:
            params = urldecode(raw)
        except ValueError:
            params = None
    elif hasattr(raw, '__iter__'):
        try:
            dict(raw)
        except ValueError:
            params = None
        except TypeError:
            params = None
        else:
            params = list(raw.items() if isinstance(raw, dict) else raw)
            params = decode_params_utf8(params)
    else:
        params = None

    return params


def generate_nonce():
    """Generate pseudorandom nonce that is unlikely to repeat.

    Per `section 3.3`_ of the OAuth 1 RFC 5849 spec.
    Per `section 3.2.1`_ of the MAC Access Authentication spec.

    A random 64-bit number is appended to the epoch timestamp for both
    randomness and to decrease the likelihood of collisions.

    .. _`section 3.2.1`: http://tools.ietf.org/html/draft-ietf-oauth-v2-http-mac-01#section-3.2.1
    .. _`section 3.3`: http://tools.ietf.org/html/rfc5849#section-3.3
    """
    return unicode_type(unicode_type(random.getrandbits(64)) + generate_timestamp())


def generate_timestamp():
    """Get seconds since epoch (UTC).

    Per `section 3.3`_ of the OAuth 1 RFC 5849 spec.
    Per `section 3.2.1`_ of the MAC Access Authentication spec.

    .. _`section 3.2.1`: http://tools.ietf.org/html/draft-ietf-oauth-v2-http-mac-01#section-3.2.1
    .. _`section 3.3`: http://tools.ietf.org/html/rfc5849#section-3.3
    """
    return unicode_type(int(time.time()))


def generate_token(length=30, chars=UNICODE_ASCII_CHARACTER_SET):
    """Generates a non-guessable OAuth token

    OAuth (1 and 2) does not specify the format of tokens except that they
    should be strings of random characters. Tokens should not be guessable
    and entropy when generating the random characters is important. Which is
    why SystemRandom is used instead of the default random.choice method.
    """
    rand = random.SystemRandom()
    return ''.join(rand.choice(chars) for x in range(length))


def add_params_to_qs(query, params):
    """Extend a query with a list of two-tuples."""
    if isinstance(query, dict):
        queryparams = query.items()
    else:
        queryparams = urlparse.parse_qsl(query, keep_blank_values=True)
    queryparams.extend(params)
    return urlencode(queryparams)


def add_params_to_uri(uri, params, fragment=False):
    """Add a list of two-tuples to the uri query components."""
    sch, net, path, par, query, fra = urlparse.urlparse(uri)
    if fragment:
        fra = add_params_to_qs(query, params)
    else:
        query = add_params_to_qs(query, params)
    return urlparse.urlunparse((sch, net, path, par, query, fra))


def safe_string_equals(a, b):
    """ Near-constant time string comparison.

    Used in order to avoid timing attacks on sensitive information such
    as secret keys during request verification (`rootLabs`_).

    .. _`rootLabs`: http://rdist.root.org/2010/01/07/timing-independent-array-comparison/

    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


def to_unicode(data, encoding):
    """Convert a number of different types of objects to unicode."""
    if isinstance(data, unicode_type):
        return data

    if isinstance(data, bytes_type):
        return unicode_type(data, encoding=encoding)

    if hasattr(data, '__iter__'):
        try:
            dict(data)
        except TypeError:
            pass
        except ValueError:
            # Assume it's a one dimensional data structure
            return (to_unicode(i, encoding) for i in data)
        else:
            # We support 2.6 which lacks dict comprehensions
            if isinstance(data, dict):
                data = data.items()
            return dict(((to_unicode(k, encoding), to_unicode(v, encoding)) for k, v in data))

    return data


class CaseInsensitiveDict(dict):
    """Basic case insensitive dict with strings only keys."""

    proxy = {}

    def __init__(self, data):
        self.proxy = dict((k.lower(), k) for k in data)
        for k in data:
            self[k] = data[k]

    def __contains__(self, k):
        return k.lower() in self.proxy

    def __delitem__(self, k):
        key = self.proxy[k.lower()]
        super(CaseInsensitiveDict, self).__delitem__(key)
        del self.proxy[k.lower()]

    def __getitem__(self, k):
        key = self.proxy[k.lower()]
        return super(CaseInsensitiveDict, self).__getitem__(key)

    def get(self, k, default=None):
        return self[k] if k in self else default

    def __setitem__(self, k, v):
        super(CaseInsensitiveDict, self).__setitem__(k, v)
        self.proxy[k.lower()] = k


class Request(object):
    """A malleable representation of a signable HTTP request.

    Body argument may contain any data, but parameters will only be decoded if
    they are one of:

    * urlencoded query string
    * dict
    * list of 2-tuples

    Anything else will be treated as raw body data to be passed through
    unmolested.
    """

    def __init__(self, uri, http_method='GET', body=None, headers=None,
            encoding='utf-8'):
        # Convert to unicode using encoding if given, else assume unicode
        encode = lambda x: to_unicode(x, encoding) if encoding else x

        self.uri = encode(uri)
        self.http_method = encode(http_method)
        self.headers = CaseInsensitiveDict(encode(headers or {}))
        self.body = encode(body)
        self.decoded_body = extract_params(encode(body))
        self.oauth_params = []

        self._params = {}
        self._params.update(dict(urldecode(self.uri_query)))
        self._params.update(dict(self.decoded_body or []))
        self._params.update(self.headers)

    def __getattr__(self, name):
        return self._params.get(name, None)

    @property
    def uri_query(self):
        return urlparse.urlparse(self.uri).query

    @property
    def uri_query_params(self):
        return urlparse.parse_qsl(self.uri_query, keep_blank_values=True,
                                  strict_parsing=True)
