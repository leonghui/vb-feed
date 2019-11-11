import validators
from flask import Flask, request, jsonify
from requests import exceptions

from vb_feed import get_latest_posts

app = Flask(__name__)


@app.route('/feed.json', methods=['GET'])
def form():
    forum_url = request.args.get('forum_url')
    thread_id = request.args.get('thread_id')

    if forum_url is None or thread_id is None:
        return 'Please provide values for both forum_url and thread_id'

    if not thread_id.isnumeric():
        return 'Invalid thread_id'

    if not isinstance(forum_url,str):
        return 'Invalid forum_url'

    if forum_url.endswith('/'):
        forum_url = forum_url.rstrip('/')

    try:
        assert validators.url(forum_url)
        output = get_latest_posts(forum_url, thread_id)
        return jsonify(output)
    except AssertionError:
        return f"Invalid url {forum_url}"
    except exceptions.RequestException:
        return f"Error generating output for thread {thread_id} at {forum_url}."


if __name__ == '__main__':
    app.run(host='0.0.0.0')
