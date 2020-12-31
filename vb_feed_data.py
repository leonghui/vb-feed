from dataclasses import dataclass, field
from requests.models import PreparedRequest


@dataclass
class QueryStatus():
    ok: bool = True
    errors: list[str] = field(default_factory=list)

    def refresh(self):
        self.ok = False if self.errors else True


@dataclass
class VbThreadQuery():
    forum_url: str
    thread_id: str
    status: QueryStatus
    username_list: list[str] = field(default_factory=list)
    usernames: str = None

    def validate_url(self):
        prepared_request = PreparedRequest()

        try:
            prepared_request.prepare_url(self.forum_url, None)
        except Exception as ex:
            self.status.errors.append('Invalid forum_url: ' + str(ex))

        if self.forum_url.endswith('/'):
            self.forum_url = self.forum_url.rstrip('/')

    def validate_thread_id(self):
        if not self.thread_id.isnumeric():
            self.status.errors.append('Invalid thread_id')

    def tokenize_usernames(self):
        if self.usernames is not None:
            assert isinstance(self.usernames, str)
            self.username_list = self.usernames.split(',')

    def __post_init__(self):
        self.validate_url()
        self.validate_thread_id()
        self.tokenize_usernames()
        self.status.refresh()
