# vb-feed
A simple Python script to generate a [JSON Feed](https://github.com/brentsimmons/JSONFeed) for threads on vBulletin forums.

Uses [BeautifulSoup 4](https://www.crummy.com/software/BeautifulSoup/) and served over [Flask!](https://github.com/pallets/flask/)

Use the [Docker build](https://hub.docker.com/r/leonghui/vb-feed) to host your own instance.

1. Set the environment variable: `FORUM_URL=https://vbulletin.org/forum`

2. Access the feed using the URL: `http://<host>/{threadid}/`

E.g.
```
Forum thread:
https://vbulletin.org/forum/showthread.php?t=322893

Feed link:
http://<host>/322893/
```

Tested with:
- [vBulletin.org Forum](https://vbulletin.org/forum/) running vBulletin 3.8.x
- [Nextcloud News App](https://github.com/nextcloud/news)
