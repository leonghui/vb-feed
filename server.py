from flask import Flask, request, jsonify, abort
from flask.logging import create_logger
from requests import exceptions

from vb_feed_data import VbThreadQuery, QueryStatus
from vb_feed import get_latest_posts

app = Flask(__name__)
app.config.update({'JSONIFY_MIMETYPE': 'application/feed+json'})
logger = create_logger(app)


def generate_response(query_object):
    if not query_object.status.ok:
        abort(400, description='Errors found: ' +
              ', '.join(query_object.status.errors))

    logger.debug(query_object)  # log values

    output = get_latest_posts(query_object, logger)

    return jsonify(output)


@app.route('/', methods=['GET'])
@app.route('/thread', methods=['GET'])
def process_query():
    forum_url = request.args.get('forum_url')
    thread_id = request.args.get('thread_id')
    usernames = request.args.get('usernames')

    vb_thread_query = VbThreadQuery(
        forum_url=forum_url, thread_id=thread_id, usernames=usernames, status=QueryStatus())

    return generate_response(vb_thread_query)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
