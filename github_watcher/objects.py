from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Optional


@dataclass
class User:
    login: str
    id: int
    type: str
    site_admin: bool
    avatar_url: str
    url: str

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def parse(user_data):
        user = User(
            login=user_data['login'],
            id=user_data['id'],
            type=user_data['type'],
            site_admin=user_data['site_admin'],
            avatar_url=user_data['avatar_url'],
            url=user_data['url']
        )
        return user


@dataclass
class Author:
    name: str
    email: str
    date: datetime

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def parse(author_data):
        return Author(
            name=author_data['name'],
            email=author_data['email'],
            date=datetime.fromisoformat(author_data['date'])
        )


class TimelineEventType(Enum):
    COMMENTED = "commented"
    COMMITTED = "committed"
    REOPENED = "reopened"
    CLOSED = "closed"
    MERGED = "merged"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_REQUEST_REMOVED = "review_request_removed"
    REVIEWED = "reviewed"
    # Add more event types as needed


@dataclass
class TimelineEvent:
    id: int
    node_id: str
    url: str
    author: User | Author
    eventType: Optional[TimelineEventType] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def parse_event(event_data: dict) -> Optional['TimelineEvent']:
        def parse_datetime(field):
            return datetime.fromisoformat(field.replace('Z', '+00:00'))

        try:
            author = Author.parse(event_data['author']) if event_data.get('author') else User.parse(event_data['actor'])
            return TimelineEvent(
                id=event_data['sha'] if event_data.get('sha') else event_data['id'],
                node_id=event_data['node_id'],
                url=event_data['url'],
                author=author,
                eventType=TimelineEventType(event_data['event']) if event_data.get('event') else None,
                created_at=parse_datetime(event_data['created_at']) if event_data.get('created_at') else None,
                updated_at=parse_datetime(event_data['updated_at']) if event_data.get('updated_at') else None
            )
        except KeyError as e:
            print(f"Error: Missing required key in event_data: {e}, event_data: {event_data}")
        except ValueError as e:
            print(f"Error: Invalid data format in event_data: {e}, event_data: {event_data}")
        except Exception as e:
            print(f"Unexpected error occurred while parsing event: {e}, event_data: {event_data}")
        return None

    @staticmethod
    def parse_events(events_data: list) -> List['TimelineEvent']:
        return [TimelineEvent.parse_event(event) for event in events_data]


@dataclass
class PullRequest:
    id: int
    number: int
    title: str
    state: str
    created_at: str
    updated_at: str
    closed_at: Optional[str]
    merged_at: Optional[str]
    draft: bool
    user: User
    html_url: str
    repo_owner: str
    repo_name: str
    timeline: Optional[List[TimelineEvent]] = None

    def to_dict(self):
        return asdict(self)

    def fetch_timeline(self, github_prs: 'GitHubPRs'):
        self.timeline = github_prs.get_pr_timeline(self.repo_owner, self.repo_name, self.number)

    @staticmethod
    def parse_pr(pr_data: dict) -> 'PullRequest':
        return PullRequest(
            id=pr_data['id'],
            number=pr_data['number'],
            title=pr_data['title'],
            state=pr_data['state'],
            created_at=pr_data['created_at'],
            updated_at=pr_data['updated_at'],
            closed_at=pr_data.get('closed_at'),
            merged_at=pr_data.get('merged_at'),
            draft=pr_data['draft'],
            user=User.parse(pr_data['user']),
            html_url=pr_data['html_url'],
            repo_owner=pr_data['html_url'].split('/')[3],
            repo_name=pr_data['html_url'].split('/')[4]
        )

    @staticmethod
    def parse_prs(prs_data: list) -> List['PullRequest']:
        return [PullRequest.parse_pr(pr) for pr in prs_data]


class PRState(Enum):
    OPEN = "open"
    CLOSED = "closed"
