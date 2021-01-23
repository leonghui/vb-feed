import bleach
from datetime import datetime, timedelta, timezone
from flask import abort
from requests import Session
from bs4 import BeautifulSoup
from dataclasses import asdict

from json_feed_data import JsonFeedTopLevel, JsonFeedItem, JsonFeedAuthor


VB_POSTS_PER_THREAD = 15
FEED_POSTS_LIMIT = 30  # default to 2 pages per feed

page_limit = FEED_POSTS_LIMIT // VB_POSTS_PER_THREAD
if page_limit < 1:
    page_limit = 1

allowed_tags = bleach.ALLOWED_TAGS.copy() + ['br', 'img', 'u']
allowed_attributes = bleach.ALLOWED_ATTRIBUTES.copy()
allowed_attributes.update({'img': ['src']})
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

    return datetime_obj.astimezone(timezone.utc)


def get_response_soup(url, logger):

    session = Session()

    logger.debug(f'Querying endpoint: {url}')

    try:
        response = session.get(url)
    except Exception as ex:
        logger.debug('Exception:' + ex)
        abort(500, description=ex)

    # return HTTP error code
    if not response.ok:
        logger.error('Error from source')
        logger.debug('Dumping input:' + response.text)
        abort(
            500, description='HTTP status from source: ' + str(response.status_code))

    # override vBulletin's wrong charset, fixes conversion issues with "smart-quotes"
    if response.encoding == 'ISO-8859-1':
        clean_response_text = str(response.content.decode('windows-1252'))
    else:
        clean_response_text = response.text

    response_soup = BeautifulSoup(clean_response_text, features='html.parser')

    return response_soup


def get_top_level_feed(thread_url, thread_soup, logger):

    header = thread_soup.head
    thread_title = header.title.get_text()

    json_feed = JsonFeedTopLevel(
        items=[],
        title=thread_title.strip(),
        home_page_url=thread_url,
    )

    page_icon = header.select_one("link[rel='shortcut icon']")
    if page_icon:
        json_feed.favicon = page_icon['href']

    thread_desc = header.select_one("meta[name='description']")
    if thread_desc:
        json_feed.description = thread_desc['content'].strip()

    return json_feed


# modified from https://stackoverflow.com/a/24893252
def remove_empty_from_dict(d):
    if isinstance(d, dict):
        return dict((k, remove_empty_from_dict(v)) for k, v in d.items() if v and remove_empty_from_dict(v))
    elif isinstance(d, list):
        return [remove_empty_from_dict(v) for v in d if v and remove_empty_from_dict(v)]
    else:
        return d


def get_latest_posts(query_object, logger):
    thread_url = query_object.forum_url + \
        "/showthread.php?t=" + query_object.thread_id

    thread_soup = get_response_soup(thread_url, logger)

    json_feed = get_top_level_feed(thread_url, thread_soup, logger)

    username_lower_list = [username.lower().strip()
                           for username in query_object.username_list]

    pagination = thread_soup.find(class_=['pagenav', 'pagination'])

    min_page = 1
    last_page = 1

    if pagination is not None:

        last_page_text = str(
            next(string for string in pagination.strings if string.startswith('Page')))

        try:
            last_page = int(str(last_page_text).split(' of ')[1])
        except ValueError:
            last_page_text_sanitized = ''.join(
                filter(str.isdigit, last_page_text))
            last_page = int(last_page_text_sanitized)

        min_page = last_page - (page_limit - 1)

    start_page = 1 if min_page < 1 else min_page

    for page in range(start_page, last_page + 1):

        page_soup = get_response_soup(thread_url + f"&page={page}", logger)

        post_section = page_soup.select_one('div#posts') if page_soup else None
        post_tables = post_section.select(
            'table[id^=post]') if post_section else None

        for post_table in post_tables:
            post_id = str(post_table['id'].replace('post', ''))
            post_url = query_object.forum_url + '/showpost.php?p=' + post_id

            post_author_soup = post_table.select_one('a.bigusername')
            post_author = post_author_soup.get_text().strip() if post_author_soup else None

            post_message_soup = post_table.select_one(
                f"div#post_message_{post_id}")

            # omit closing slash in void tags like br and remove carriage returns
            post_content = post_message_soup.encode(
                formatter='html5').decode() if post_message_soup else ''
            post_content = post_content.replace(
                '\n', '').replace('\r', '').replace('\t', '')

            post_title_list = [json_feed.title, f"Page {page}"]

            if query_object.username_list:
                post_title_list.append(
                    f"Posts by {', '.join(query_object.username_list)}")

            feed_item = JsonFeedItem(
                id=post_url,
                url=post_url,
                title=' - '.join(post_title_list).strip(),
                content_html=bleach.clean(
                    post_content,
                    tags=allowed_tags,
                    attributes=allowed_attributes,
                    strip=True
                ),
                authors=(JsonFeedAuthor(name=post_author)),
                author=JsonFeedAuthor(name=post_author)
            )

            post_datetime_text = None

            for cell in post_table.select('tr td.thead'):
                cell.a.decompose()
                for string in cell.stripped_strings:
                    if not string.startswith('#'):
                        post_datetime_text = string

            if post_datetime_text is not None:
                post_datetime = extract_datetime(post_datetime_text)
                feed_item.date_published = post_datetime.isoformat('T')

            if not username_lower_list or (post_author.lower() in username_lower_list):
                json_feed.items.append(feed_item)

    return remove_empty_from_dict(asdict(json_feed))
