# vb-feed
A simple Python script to generate a [JSON Feed](https://github.com/brentsimmons/JSONFeed) for threads on vBulletin forums.

Uses [BeautifulSoup 4](https://www.crummy.com/software/BeautifulSoup/) and served over [Flask!](https://github.com/pallets/flask/)

Use the [Docker build](https://hub.docker.com/r/leonghui/vb-feed) to host your own instance.

1. Access the feed using the URL: `http://<host>/feed.json?forum_url={url}&thread_id={id}`

2. Optionally, filter by user names: `http://<host>/feed.json?forum_url={url}&thread_id={id}&usernames={user1,user2}`

E.g.
```
Forum thread:
https://vbulletin.org/forum/showthread.php?t=322893

Feed link:
http://<host>/feed.json?forum_url=https://vbulletin.org/forum&thread_id=322893

Filtered feed link:
http://<host>/feed.json?forum_url=https://vbulletin.org/forum&thread_id=322893&usernames=Paul M,Dave
```

Tested with:
- [vBulletin.org Forum](https://vbulletin.org/forum/) running vBulletin 3.8.x
- [Nextcloud News App](https://github.com/nextcloud/news)
