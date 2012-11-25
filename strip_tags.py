'''
strip_tags maintains byte position of all visible text in an HTML
document and removes all of parts that are not visible in a web
browser.  This allows taggers to operate on the visible-only text and
any standoff taggs can refer to the original byte positions.
'''

import re
## regex to identify all HTML tags, including SCRIPT and STYLE tags
invisible = re.compile('(?P<before>(.|\n)*?)(?P<invisible>(<script(.|\n)*?</script>|<style(.|\n)*?</style>|<(.|\n)*?>))', re.I)

def strip_tags(html):
    '''
    Takes an HTML-like binary string as input and returns a binary
    string of the same length with all tags replaced by whitespace.
    This also detects script and style tags, and replaces the text
    between them with whitespace.  

    Pre-existing whitespace of any kind (newlines, tabs) is converted
    to single spaces ' ', which has the same byte length (and
    character length).

    Note: this does not change any characters like &rsquo; and &nbsp;,
    so taggers operating on this text must cope with such symbols.
    Converting them to some other character would change their byte
    length, even if equivalent from a character perspective.
    '''
    text = ''
    for m in invisible.finditer(html):
        text += m.group('before')
        text += ' ' * len(m.group('invisible'))

    ## text better be >= original
    assert len(html) >= len(text), '%d !>= %d' % (len(html), len(text))

    ## capture any characters after the last tag... such as newlines
    tail = len(html) - len(text)
    text += html[-tail:]

    ## now they must be equal
    assert len(html) == len(text), '%d != %d' % (len(html), len(text))

    return text


if __name__ == '__main__':
    print strip_tags(open('sample-input.html').read())

