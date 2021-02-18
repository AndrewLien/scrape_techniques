import requests
from lxml import etree
from io import StringIO


def getPage(url):
    response = StringIO(requests.get(url).text)
    return etree.parse(response, etree.HTMLParser())


books = [
    'matthew',
    'mark',
    'luke',
    'john',
    'acts',
]

output = open('output.txt', 'w')

for book in books:
    chapter = 1
    output.write(book + '\n')
    while True:
        url = 'https://www.biblestudytools.com/esv/{}/{}.html'.format(book, chapter)
        tree = getPage(url)
        if 'Error on Page' in requests.get(url).text:
            print('End of book.')
            break
        else:
            headers = tree.xpath('//div[@class="scripture verse-padding"]/h2//text()')
            string = str(chapter) + ': ' + ','.join(headers) + '\n'
            output.write(string)
            print('Got {} {}'.format(book, chapter))
            chapter += 1

output.close()