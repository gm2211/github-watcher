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

    def __str__(self):
        return self.value


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
        """Convert TimelineEvent to a dictionary for serialization"""
        return {
            'id': self.id,
            'node_id': self.node_id,
            'url': self.url,
            'author': self.author.to_dict() if self.author else None,
            'eventType': self.eventType.value if self.eventType else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TimelineEvent':
        """Create TimelineEvent from a dictionary"""
        # Convert string back to enum if present
        event_type = TimelineEventType(data['eventType']) if data.get('eventType') else None
        
        # Parse author data
        author_data = data.get('author')
        if author_data:
            if 'email' in author_data:
                author = Author.parse(author_data)
            else:
                author = User.parse(author_data)
        else:
            author = None

        # Parse dates
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None

        return cls(
            id=data['id'],
            node_id=data['node_id'],
            url=data['url'],
            author=author,
            eventType=event_type,
            created_at=created_at,
            updated_at=updated_at
        )

    @staticmethod
    def parse_events(events_data: list) -> List['TimelineEvent']:
        """Parse a list of timeline events from GitHub API data"""
        parsed_events = []
        for event in events_data:
            event_type = None
            if event.get('event') == 'commented':
                event_type = TimelineEventType.COMMENTED
            elif event.get('event') == 'committed':
                event_type = TimelineEventType.COMMITTED
            elif event.get('event') == 'reopened':
                event_type = TimelineEventType.REOPENED
            elif event.get('event') == 'closed':
                event_type = TimelineEventType.CLOSED
            elif event.get('event') == 'merged':
                event_type = TimelineEventType.MERGED
            elif event.get('event') == 'review_requested':
                event_type = TimelineEventType.REVIEW_REQUESTED
            elif event.get('event') == 'review_request_removed':
                event_type = TimelineEventType.REVIEW_REQUEST_REMOVED
            elif event.get('event') == 'reviewed':
                event_type = TimelineEventType.REVIEWED

            if event_type:
                try:
                    # Parse author/actor data
                    author_data = event.get('author') or event.get('actor')
                    if author_data:
                        if 'email' in author_data:
                            author = Author.parse(author_data)
                        else:
                            author = User.parse(author_data)
                    else:
                        author = None

                    # Create TimelineEvent
                    parsed_event = TimelineEvent(
                        id=event.get('sha') or event.get('id'),
                        node_id=event.get('node_id', ''),
                        url=event.get('url', ''),
                        author=author,
                        eventType=event_type,
                        created_at=datetime.fromisoformat(event['created_at'].replace('Z', '+00:00')) if event.get('created_at') else None,
                        updated_at=datetime.fromisoformat(event['updated_at'].replace('Z', '+00:00')) if event.get('updated_at') else None
                    )
                    parsed_events.append(parsed_event)
                except Exception as e:
                    print(f"Error parsing event: {e}, event data: {event}")
                    continue

        return parsed_events


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
