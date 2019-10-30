from datetime import datetime, date, timedelta

import requests
from bs4 import BeautifulSoup

FORUM_NAME = 'name'
FORUM_URL = 'https://forums.name.com'
JSONFEED_VERSION_URL = 'https://jsonfeed.org/version/1'

VB_POSTS_PER_THREAD = 15
FEED_POSTS_LIMIT = 30  # default to 2 pages per feed

page_limit = FEED_POSTS_LIMIT // VB_POSTS_PER_THREAD
if page_limit < 1:
    page_limit = 1


def get_latest_posts(thread_id):
    thread_uri = f"/showthread.php?t={thread_id}"
    thread_request = requests.get(FORUM_URL + thread_uri)

    # return HTTP error code
    if not thread_request.ok:
        return f"Error {thread_request.status_code}"

    page_soup = BeautifulSoup(thread_request.text, features='html.parser')

    header = page_soup.head
    page_icon = header.select_one("link[rel='SHORTCUT ICON']")['href']
    thread_title = header.select_one("meta[property='og:title']")['content']
    thread_desc = header.select_one("meta[name='description']")['content']

    output = {
        'version': JSONFEED_VERSION_URL,
        'title': ' - '.join((thread_title, FORUM_NAME)),
        'home_page_url': FORUM_URL + thread_uri,
        'description': thread_desc,
        'favicon': page_icon
    }

    pagination = page_soup.select_one('div.pagination')
    last_page_text = pagination.span.string.split(' of ')[1]

    try:
        last_page = int(last_page_text)
    except ValueError:
        last_page_text_sanitized = ''.join(filter(str.isdigit, last_page_text))
        last_page = int(last_page_text_sanitized)

    min_page = last_page - (page_limit - 1)

    start_page = 1 if min_page < 1 else min_page

    items_list = []

    for page in range(start_page, last_page + 1):

        page_request = requests.get(FORUM_URL + thread_uri + f"&page={page}")

        # return HTTP error code
        if not page_request.ok:
            return f"Error {page_request.status_code}"

        page_soup = BeautifulSoup(page_request.text, features='html.parser')

        thread_content = page_soup.select_one('div#posts')

        post_tables = thread_content.select('table.post')

        for post_table in post_tables:
            post_id = post_table['id'].replace('post', '')

            status_row = post_table.select_one('tr:first-of-type')

            post_datetime_tag = status_row.select_one('tr td.thead')
            post_datetime_text = post_datetime_tag.get_text().strip()

            if post_datetime_text.startswith('Today'):
                post_datetime = datetime.combine(
                    date.today(),
                    datetime.strptime(post_datetime_text, 'Today, %I:%M %p').time()
                )
            elif post_datetime_text.startswith('Yesterday'):
                post_datetime = datetime.combine(
                    date.today() - timedelta(days=1),
                    datetime.strptime(post_datetime_text, 'Yesterday, %I:%M %p').time()
                )
            else:
                post_datetime = datetime.strptime(post_datetime_text, '%d-%m-%Y, %I:%M %p')

            post_datetime_formatted = post_datetime.isoformat('T')

            post_uri_tag = status_row.select_one(f"#postcount{post_id}")
            post_uri = post_uri_tag['href']
            post_url = FORUM_URL + post_uri

            body_row = post_table.select_one('tr:nth-of-type(2)')
            post_author = body_row.select_one(f"#postmenu_{post_id} a").string
            post_message = body_row.select_one(f"#post_message_{post_id}")

            item = {
                'id': post_url,
                'url': post_url,
                'title': ' - '.join((thread_title, f"Page {page}")),
                'content_text': post_message.get_text(),
                'date_published': post_datetime_formatted,
                'author': {
                    'name': post_author
                }
            }

            items_list.append(item)

    output['items'] = items_list

    return output
