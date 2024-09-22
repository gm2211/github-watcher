from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Optional


@dataclass
class User:
    login: str
    id: int
    avatar_url: str

    def to_dict(self):
        return asdict(self)


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
    actor: User
    event: TimelineEventType
    created_at: datetime
    updated_at: Optional[datetime] = None

    def to_dict(self):
        return {
            'id': self.id,
            'node_id': self.node_id,
            'url': self.url,
            'actor': self.actor.to_dict(),
            'event': self.event.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def parse_event(event_data: dict) -> 'TimelineEvent':
        return TimelineEvent(
            id=event_data['id'],
            node_id=event_data['node_id'],
            url=event_data['url'],
            actor=User(
                login=event_data['actor']['login'],
                id=event_data['actor']['id'],
                avatar_url=event_data['actor']['avatar_url']
            ),
            event=TimelineEventType(event_data['event']),
            created_at=datetime.fromisoformat(event_data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(event_data['updated_at'].replace('Z', '+00:00')) if event_data.get(
                'updated_at'
            ) else None
        )

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
    timeline: Optional[List[TimelineEvent]] = None

    def to_dict(self):
        pr_dict = asdict(self)
        pr_dict['user'] = self.user.to_dict()
        pr_dict['created_at'] = self.created_at
        pr_dict['updated_at'] = self.updated_at
        pr_dict['closed_at'] = self.closed_at
        pr_dict['merged_at'] = self.merged_at
        if self.timeline:
            pr_dict['timeline'] = [event.to_dict() for event in self.timeline]
        return pr_dict

    def fetch_timeline(self, github_prs: 'GitHubPRs'):
        repo_owner, repo_name = self.html_url.split('/')[3:5]
        self.timeline = github_prs.get_pr_timeline(repo_owner, repo_name, self.number)

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
            user=User(
                login=pr_data['user']['login'],
                id=pr_data['user']['id'],
                avatar_url=pr_data['user']['avatar_url']
            ),
            html_url=pr_data['html_url']
        )

    @staticmethod
    def parse_prs(prs_data: list) -> List['PullRequest']:
        return [PullRequest.parse_pr(pr) for pr in prs_data]


class PRState(Enum):
    OPEN = "open"
    CLOSED = "closed"
