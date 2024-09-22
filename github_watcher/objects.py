from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    login: str
    id: int
    avatar_url: str


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
    def parse_prs(prs_data: list) -> list['PullRequest']:
        return [PullRequest.parse_pr(pr) for pr in prs_data]
