import logging
import os
import re
from datetime import datetime, timedelta

import bleach
import requests
from bs4 import BeautifulSoup

FORUM_URL = os.environ['FORUM_URL']
JSONFEED_VERSION_URL = 'https://jsonfeed.org/version/1'

VB_POSTS_PER_THREAD = 15
FEED_POSTS_LIMIT = 30  # default to 2 pages per feed

page_limit = FEED_POSTS_LIMIT // VB_POSTS_PER_THREAD
if page_limit < 1:
    page_limit = 1

allowed_tags = bleach.ALLOWED_TAGS.copy() + ['br', 'u']
allowed_tags.remove('a')


def extract_datetime(text):
    datetime_formats = [
        'Today, %I:%M %p',
        'Today, %H:%M',
        'Yesterday, %I:%M %p',
        'Yesterday, %H:%M',
        '%d-%m-%Y, %I:%M %p',
        '%d %b %Y, %H:%M'
    ]

    # default timestamp
    datetime_obj = datetime.now()

    for datetime_format in datetime_formats:
        try:
            datetime_obj = datetime.strptime(text, datetime_format)
        except ValueError:
            pass

    formatted_date = None

    if text.startswith('Today'):
        formatted_date = datetime.now()
    elif text.startswith('Yesterday'):
        formatted_date = datetime.now() - timedelta(days=1)

    if formatted_date is not None:
        datetime_obj = datetime_obj.replace(
            year=formatted_date.year, month=formatted_date.month, day=formatted_date.day,
            tzinfo=formatted_date.astimezone().tzinfo
        )

    return datetime_obj


def get_latest_posts(thread_id):
    thread_uri = f"/showthread.php?t={thread_id}"
    thread_response = requests.get(FORUM_URL + thread_uri)

    # return HTTP error code
    if not thread_response.ok:
        return f"Error {thread_response.status_code}"

    # override vBulletin's wrong charset, fixes conversion issues with "smart-quotes"
    if thread_response.encoding == 'ISO-8859-1':
        thread_content = str(thread_response.content.decode('windows-1252'))
    else:
        thread_content = thread_response.text

    thread_soup = BeautifulSoup(thread_content, features='html.parser')

    header = thread_soup.head
    thread_title = header.title.get_text()

    output = {
        'version': JSONFEED_VERSION_URL,
        'title': thread_title.strip(),
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
            output['description'] = thread_desc.strip()
    except TypeError:
        logging.info('Description not found')

    pagination = thread_soup.find(class_=['pagenav', 'pagination'])

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

        page_response = requests.get(FORUM_URL + thread_uri + f"&page={page}")

        # return HTTP error code
        if not page_response.ok:
            return f"Error {page_response.status_code}"

        # override vBulletin's wrong charset, fixes conversion issues with "smart-quotes"
        if page_response.encoding == 'ISO-8859-1':
            page_content = str(page_response.content.decode('windows-1252'))
        else:
            page_content = page_response.text

        page_soup = BeautifulSoup(page_content, features='html.parser')

        post_section = page_soup.select_one('div#posts')

        try:
            post_tables = post_section.find_all('table', class_='tborder', id=re.compile('^post'))
        except AttributeError:
            return "Error no posts found."

        for post_table in post_tables:
            post_id = str(post_table['id'].replace('post', ''))

            status_row = post_table.select_one('tr:first-of-type')
            post_url = FORUM_URL + f"/showpost.php?p={post_id}"

            post_author = post_table.find(id=f"postmenu_{post_id}").a
            post_message = post_table.find(id=f"post_message_{post_id}")

            # omit closing slash in void tags like br and remove carriage returns
            post_content = post_message.encode(formatter='html5').decode()
            post_content = post_content.replace('\n', '')
            post_content = post_content.replace('\r', '')

            # remove tabs
            post_content = post_content.replace('\t', '')

            item = {
                'id': post_url,
                'url': post_url,
                'title': ' - '.join((thread_title, f"Page {page}")).strip(),
                'content_html': bleach.clean(
                    post_content,
                    tags=allowed_tags,
                    strip=True
                ),
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
                post_datetime = extract_datetime(post_datetime_text)
                item['date_published'] = post_datetime.isoformat('T')

            items_list.append(item)

    output['items'] = items_list

    return output
