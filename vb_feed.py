import logging
import os
import re
from datetime import datetime, date, timedelta

import requests
from bs4 import BeautifulSoup

FORUM_URL = os.environ['FORUM_URL']
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
    thread_title = header.title.get_text()

    output = {
        'version': JSONFEED_VERSION_URL,
        'title': thread_title,
        'home_page_url': FORUM_URL + thread_uri
    }

    try:
        page_icon = header.select_one("link[rel='shortcut icon']")['href']
        if page_icon:
            output['favicon'] = page_icon
    except TypeError:
        logging.info('Favicon not found')

    try:
        thread_desc = header.select_one("meta[name='description']")['content']
        if thread_desc:
            output['description'] = thread_desc
    except TypeError:
        logging.info('Description not found')

    pagination = page_soup.find(class_=['pagenav', 'pagination'])

    min_page = 1
    last_page = 1

    if pagination is not None:

        last_page_text = str(next(string for string in pagination.strings if string.startswith('Page')))

        try:
            last_page = int(str(last_page_text).split(' of ')[1])
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

        post_tables = thread_content.find_all('table', class_='tborder', id=re.compile('^post'))

        for post_table in post_tables:
            post_id = str(post_table['id'].replace('post', ''))

            status_row = post_table.select_one('tr:first-of-type')
            post_url = FORUM_URL + f"/showpost.php?p={post_id}"

            post_author = post_table.find(id=f"postmenu_{post_id}").a
            post_message = post_table.find(id=f"post_message_{post_id}")

            item = {
                'id': post_url,
                'url': post_url,
                'title': ' - '.join((thread_title, f"Page {page}")),
                'content_text': post_message.get_text(),
                'author': {
                    'name': post_author.get_text()
                }
            }

            post_datetime_text = None

            for cell in status_row.select('tr td.thead'):
                cell.a.decompose()
                for string in cell.stripped_strings:
                    if not string.startswith('#'):
                        post_datetime_text = string

            if post_datetime_text is not None:
                if post_datetime_text.startswith('Today'):
                    # try 12H and 24H formats
                    try:
                        post_time = datetime.strptime(post_datetime_text, 'Today, %I:%M %p').time()
                    except ValueError:
                        post_time = datetime.strptime(post_datetime_text, 'Today, %H:%M').time()

                    post_datetime = datetime.combine(date.today(), post_time)
                elif post_datetime_text.startswith('Yesterday'):
                    # try 12H and 24H formats
                    try:
                        post_time = datetime.strptime(post_datetime_text, 'Yesterday, %I:%M %p').time()
                    except ValueError:
                        post_time = datetime.strptime(post_datetime_text, 'Yesterday, %H:%M').time()

                    post_datetime = datetime.combine(date.today() - timedelta(days=1), post_time)
                else:
                    try:
                        post_datetime = datetime.strptime(post_datetime_text, '%d-%m-%Y, %I:%M %p')
                    except ValueError:
                        post_datetime = datetime.strptime(post_datetime_text, '%d %b %Y, %H:%M')

                post_datetime_formatted = post_datetime.isoformat('T')

                item['date_published'] = post_datetime_formatted

            items_list.append(item)

    output['items'] = items_list

    return output
