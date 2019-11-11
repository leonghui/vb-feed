from flask import Flask, request, jsonify
from requests import exceptions

from vb_feed import get_latest_posts

app = Flask(__name__)


@app.route('/feed.json', methods=['GET'])
def form():
    forum_url = request.args.get('forum_url')
    thread_id = request.args.get('thread_id')

    if forum_url is not None and thread_id is not None:
        if forum_url.endswith('/'):
            forum_url = forum_url.rstrip('/')

        try:
            output = get_latest_posts(forum_url, thread_id)
            return jsonify(output)
        except exceptions.RequestException:
            return f"Error generating output for thread {thread_id} at {forum_url}."
    else:
        return 'Please provide values for both forum_url and thread_id'


if __name__ == '__main__':
    app.run(host='0.0.0.0')
