from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

from github_pr_watcher.utils import parse_datetime


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
            login=user_data["login"],
            id=user_data["id"],
            type=user_data["type"],
            site_admin=user_data["site_admin"],
            avatar_url=user_data["avatar_url"],
            url=user_data["url"],
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
            name=author_data["name"],
            email=author_data["email"],
            date=datetime.fromisoformat(author_data["date"]),
        )


class TimelineEventType(Enum):
    COMMENTED = "commented"
    REVIEWED = "reviewed"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    MERGED = "merged"
    CLOSED = "closed"
    REOPENED = "reopened"
    COMMITTED = "committed"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, event_type_str) -> "TimelineEventType":
        """Safely convert string to TimelineEventType"""
        # If we're already dealing with an enum, return it
        if isinstance(event_type_str, TimelineEventType):
            return event_type_str

        try:
            # Handle None case
            if event_type_str is None:
                return cls.UNKNOWN

            # Ensure we're working with a string
            event_type_str = str(event_type_str).lower()

            # Map GitHub API event types to our enum values
            event_map = {
                "committed": cls.COMMITTED,
                "commented": cls.COMMENTED,
                "reviewed": cls.REVIEWED,
                "changes_requested": cls.CHANGES_REQUESTED,
                "approved": cls.APPROVED,
                "merged": cls.MERGED,
                "closed": cls.CLOSED,
                "reopened": cls.REOPENED,
            }
            return event_map.get(event_type_str, cls.UNKNOWN)
        except Exception as e:
            print(
                f"Warning: Error converting event type '{event_type_str}': {e}, treating as UNKNOWN"
            )
            return cls.UNKNOWN

    def __str__(self):
        return self.value


@dataclass
class TimelineEvent:
    id: int
    node_id: str
    url: str
    # Should ideally not be none, but doing this if parsing errors
    author: Optional[User | Author] = None
    eventType: Optional[TimelineEventType] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self):
        """Convert TimelineEvent to a dictionary for serialization"""
        try:
            # Always convert eventType to string value for serialization
            if isinstance(self.eventType, TimelineEventType):
                event_type_str = self.eventType.value
            elif self.eventType is None:
                event_type_str = None
            else:
                event_type_str = str(self.eventType)

            return {
                "id": self.id,
                "node_id": self.node_id,
                "url": self.url,
                "author": self.author.to_dict() if self.author else None,
                "eventType": event_type_str,  # Now always a string or None
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        except Exception as e:
            print(f"Error converting event to dict: {e}")
            return {
                "id": self.id,
                "node_id": self.node_id,
                "url": self.url,
                "author": None,
                "eventType": None,
                "created_at": None,
                "updated_at": None,
            }

    @classmethod
    def parse_event(cls, data: dict) -> "TimelineEvent":
        """Create TimelineEvent from a dictionary"""
        try:
            # Convert string back to enum if present
            event_type = None
            if event_type_str := data.get("eventType"):
                event_type = TimelineEventType.from_string(event_type_str)

            # Parse author data
            author_data = data.get("author")
            if author_data:
                if isinstance(author_data.get("date"), datetime):
                    # If date is already a datetime object, convert it to string first
                    author_data["date"] = author_data["date"].isoformat()
                if "email" in author_data:
                    author = Author.parse(author_data)
                else:
                    author = User.parse(author_data)
            else:
                author = None

            # Parse dates
            created_at = None
            updated_at = None
            if created_at_data := data.get("created_at"):
                if isinstance(created_at_data, str):
                    created_at = datetime.fromisoformat(created_at_data)
                elif isinstance(created_at_data, datetime):
                    created_at = created_at_data

            if updated_at_data := data.get("updated_at"):
                if isinstance(updated_at_data, str):
                    updated_at = datetime.fromisoformat(updated_at_data)
                elif isinstance(updated_at_data, datetime):
                    updated_at = updated_at_data

            return cls(
                id=data["id"],
                node_id=data["node_id"],
                url=data["url"],
                author=author,
                eventType=event_type,
                created_at=created_at,
                updated_at=updated_at,
            )
        except Exception as e:
            print(f"Error parsing event: {e}")
            return cls(
                id=data.get("id", 0),
                node_id=data.get("node_id", ""),
                url=data.get("url", ""),
                author=None,
                eventType=TimelineEventType.UNKNOWN,
                created_at=None,
                updated_at=None,
            )

    @staticmethod
    def parse_events(events_data: list) -> List["TimelineEvent"]:
        """Parse a list of timeline events from GitHub API data"""
        parsed_events = []
        for event in events_data:
            try:
                # Determine event type based on event type or state
                event_type = TimelineEventType.UNKNOWN

                # Check for review events
                if event.get("event") == "reviewed":
                    if state := event.get("state", "").lower():
                        if state == "approved":
                            event_type = TimelineEventType.APPROVED
                        elif state == "changes_requested":
                            event_type = TimelineEventType.CHANGES_REQUESTED
                        else:
                            event_type = TimelineEventType.REVIEWED
                # Check for other event types
                elif event.get("event") == "commented":
                    event_type = TimelineEventType.COMMENTED
                elif event.get("event") == "merged":
                    event_type = TimelineEventType.MERGED
                elif event.get("event") == "closed":
                    event_type = TimelineEventType.CLOSED
                elif event.get("event") == "reopened":
                    event_type = TimelineEventType.REOPENED
                elif "commit_id" in event:
                    event_type = TimelineEventType.COMMITTED

                # Parse author/actor data
                author_data = event.get("author") or event.get("actor")
                if author_data:
                    try:
                        if "email" in author_data:
                            author = Author.parse(author_data)
                        else:
                            author = User.parse(author_data)
                    except Exception as e:
                        print(f"Error parsing author: {e}")
                        author = None
                else:
                    author = None

                # Parse dates carefully
                created_at = None
                updated_at = None

                if created_at_str := event.get("created_at"):
                    if isinstance(created_at_str, str):
                        created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )

                if updated_at_str := event.get("updated_at"):
                    if isinstance(updated_at_str, str):
                        updated_at = datetime.fromisoformat(
                            updated_at_str.replace("Z", "+00:00")
                        )

                parsed_event = TimelineEvent(
                    id=event.get("sha") or event.get("id"),
                    node_id=event.get("node_id", ""),
                    url=event.get("url", ""),
                    author=author,
                    eventType=event_type,
                    created_at=created_at,
                    updated_at=updated_at,
                )

                parsed_events.append(parsed_event)

            except Exception as e:
                print(f"Error parsing event: {e}")
                continue

        return parsed_events


@dataclass
class PullRequest:
    id: int
    number: int
    title: str
    state: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    merged_at: Optional[datetime]
    draft: bool
    user: User
    html_url: str
    repo_owner: str
    repo_name: str
    archived: bool = False
    timeline: Optional[List[TimelineEvent]] = None
    changed_files: Optional[int] = None
    additions: Optional[int] = None
    deletions: Optional[int] = None
    comment_count_by_author: Optional[Dict[str, int]] = None
    last_comment_time: Optional[datetime] = None
    last_comment_author: Optional[str] = None
    approved_by: Optional[List[str]] = None
    latest_reviews: Optional[Dict[str, str]] = None
    merged: bool = False
    merged_by: Optional[str] = None

    def to_dict(self):
        """Convert PullRequest to a dictionary for serialization"""
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "state": self.state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "merged_at": self.merged_at.isoformat() if self.merged_at else None,
            "draft": self.draft,
            "user": self.user.to_dict() if self.user else None,
            "html_url": self.html_url,
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "archived": self.archived,
            "timeline": (
                [event.to_dict() for event in self.timeline] if self.timeline else None
            ),
            "changed_files": self.changed_files,
            "additions": self.additions,
            "deletions": self.deletions,
            "comment_count_by_author": self.comment_count_by_author,
            "last_comment_time": (
                self.last_comment_time.isoformat() if self.last_comment_time else None
            ),
            "last_comment_author": self.last_comment_author,
            "approved_by": self.approved_by,
            "latest_reviews": self.latest_reviews,
            "merged": self.merged,
            "merged_by": self.merged_by,
        }

    @staticmethod
    def parse_pr(pr_data: dict) -> "PullRequest":
        """Create PullRequest from a dictionary"""
        try:
            # Parse timeline if present
            timeline = None
            if timeline_data := pr_data.get("timeline"):
                timeline = [
                    TimelineEvent.parse_event(event) for event in timeline_data if event
                ]

            # Ensure required fields exist
            if "state" not in pr_data:
                pr_data["state"] = "unknown"  # Provide a default state

            pr = PullRequest(
                id=pr_data["id"],
                number=pr_data["number"],
                title=pr_data["title"],
                state=pr_data["state"],
                created_at=parse_datetime(pr_data["created_at"]),
                updated_at=parse_datetime(pr_data["updated_at"]),
                closed_at=parse_datetime(pr_data.get("closed_at")),
                merged_at=parse_datetime(pr_data.get("merged_at")),
                draft=pr_data.get("draft", False),
                user=User.parse(pr_data["user"]),
                html_url=pr_data["html_url"],
                repo_owner=pr_data["repo_owner"],
                repo_name=pr_data["repo_name"],
                archived=pr_data.get("archived", False),
                timeline=timeline,
                changed_files=pr_data.get("changed_files"),
                additions=pr_data.get("additions"),
                deletions=pr_data.get("deletions"),
                comment_count_by_author=pr_data.get("comment_count_by_author"),
                last_comment_time=parse_datetime(pr_data.get("last_comment_time")),
                last_comment_author=pr_data.get("last_comment_author"),
                approved_by=pr_data.get("approved_by"),
                latest_reviews=pr_data.get("latest_reviews"),
                merged=pr_data.get("merged", False),
                merged_by=pr_data.get("merged_by"),
            )

            return pr

        except Exception as e:
            print(f"Error parsing PR: {e}")
            raise

    @staticmethod
    def parse_prs(prs_data: list) -> List["PullRequest"]:
        return [PullRequest.parse_pr(pr) for pr in prs_data]


class PRState(Enum):
    OPEN = "open"
    CLOSED = "closed"
