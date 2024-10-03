import pygame
import sys
import webbrowser
from objects import PullRequest
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Union

# Initialize Pygame
pygame.init()

# Set up the display
width, height = 1200, 800  # Increased width to accommodate more information
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("GitHub Watcher")

# Colors
BACKGROUND = (240, 240, 240)
HEADER = (60, 60, 60)
SECTION_BG = (255, 255, 255)
TEXT = (30, 30, 30)
HIGHLIGHT = (0, 120, 215)
PR_BG = (245, 245, 245)
PR_HOVER = (230, 230, 230)
STATUS_COLORS = {
    "open": (75, 181, 67),  # Green
    "closed": (203, 36, 49),  # Red
    "merged": (161, 88, 207)  # Purple
}

# Fonts
title_font = pygame.font.Font(None, 48)
section_font = pygame.font.Font(None, 36)
author_font = pygame.font.Font(None, 28)
pr_font = pygame.font.Font(None, 24)
stats_font = pygame.font.Font(None, 20)

def draw_text(text: str, font: pygame.font.Font, color: Tuple[int, int, int], x: int, y: int, align: str = "left") -> pygame.Rect:
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if align == "center":
        text_rect.centerx = x
    elif align == "right":
        text_rect.right = x
    else:
        text_rect.left = x
    text_rect.top = y
    screen.blit(text_surface, text_rect)
    return text_rect

def get_pr_age(created_at: Union[str, datetime]) -> str:
    now = datetime.now(timezone.utc)
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age = now - created_at
    if age.days > 0:
        return f"{age.days}d"
    elif age.seconds // 3600 > 0:
        return f"{age.seconds // 3600}h"
    else:
        return f"{age.seconds // 60}m"

def draw_pr_sections(pr_sections: Dict[str, Dict[str, List[Dict[str, Any]]]], scroll_y: int, mouse_pos: Tuple[int, int]) -> Tuple[List[Tuple[pygame.Rect, str]], int]:
    y_offset = 120 - scroll_y
    clickable_areas = []

    for section, authors in pr_sections.items():
        pygame.draw.rect(screen, SECTION_BG, (50, y_offset, width - 100, 50))
        draw_text(section, section_font, HIGHLIGHT, width // 2, y_offset + 10, align="center")
        y_offset += 60

        for author, prs in authors.items():
            draw_text(author, author_font, TEXT, 70, y_offset)
            y_offset += 35

            for pr in prs:
                pr_rect = pygame.Rect(70, y_offset, width - 140, 60)  # Increased height for more info
                if pr_rect.collidepoint(mouse_pos[0], mouse_pos[1] + scroll_y):
                    pygame.draw.rect(screen, PR_HOVER, pr_rect)
                else:
                    pygame.draw.rect(screen, PR_BG, pr_rect)
                
                # Draw PR title
                draw_text(pr["title"], pr_font, TEXT, 80, y_offset + 5)
                
                # Draw PR stats
                comments = pr.get('comments', 'N/A')
                stats_text = f"Comments: {comments} | Age: {get_pr_age(pr['created_at'])} | Status: {pr['state']}"
                draw_text(stats_text, stats_font, TEXT, 80, y_offset + 30)
                
                # Draw status indicator
                status_color = STATUS_COLORS.get(pr['state'].lower(), TEXT)
                pygame.draw.circle(screen, status_color, (width - 160, y_offset + 30), 8)
                
                clickable_areas.append((pr_rect, pr["url"]))
                y_offset += 65  # Increased spacing between PRs

        y_offset += 20

    return clickable_areas, y_offset + scroll_y

def organize_prs_by_section_and_author(
    user_open_prs: Dict[str, List[PullRequest]],
    user_awaiting_review: Dict[str, List[PullRequest]],
    prs_that_need_attention: Dict[str, List[PullRequest]],
    user_recently_closed_prs: Dict[str, List[PullRequest]],
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    pr_sections: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "Needs Review": {},
        "Changes Requested": {},
        "Open PRs": {},
        "Recently Closed": {},
    }

    def add_pr_to_section(section: str, pr: PullRequest) -> None:
        user_login = pr.user.login if hasattr(pr.user, 'login') else str(pr.user)
        if user_login not in pr_sections[section]:
            pr_sections[section][user_login] = []
        pr_sections[section][user_login].append({
            "title": f"PR {pr.number}: {pr.title}",
            "url": pr.html_url,
            "comments": getattr(pr, 'comments', 'N/A'),
            "created_at": pr.created_at,
            "state": pr.state
        })

    for user, prs in user_awaiting_review.items():
        for pr in prs:
            add_pr_to_section("Needs Review", pr)

    for user, prs in prs_that_need_attention.items():
        for pr in prs:
            add_pr_to_section("Changes Requested", pr)

    for user, prs in user_open_prs.items():
        for pr in prs:
            if pr not in user_awaiting_review.get(user, []) and pr not in prs_that_need_attention.get(user, []):
                add_pr_to_section("Open PRs", pr)

    for user, prs in user_recently_closed_prs.items():
        for pr in prs:
            add_pr_to_section("Recently Closed", pr)

    return pr_sections

def open_ui(user_open_prs: Dict[str, List[PullRequest]], user_awaiting_review: Dict[str, List[PullRequest]], prs_that_need_attention: Dict[str, List[PullRequest]], user_recently_closed_prs: Dict[str, List[PullRequest]]) -> None:
    running = True
    pr_sections = organize_prs_by_section_and_author(
        user_open_prs, user_awaiting_review, prs_that_need_attention, user_recently_closed_prs
    )

    scroll_y = 0
    max_scroll = 0
    clock = pygame.time.Clock()
    clickable_areas: List[Tuple[pygame.Rect, str]] = []

    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    for area, url in clickable_areas:
                        if area.collidepoint(mouse_pos[0], mouse_pos[1] + scroll_y):
                            webbrowser.open(url)
                elif event.button == 4:  # Scroll up
                    scroll_y = max(0, scroll_y - 30)
                elif event.button == 5:  # Scroll down
                    scroll_y = min(max_scroll, scroll_y + 30)

        # Clear the screen
        screen.fill(BACKGROUND)

        # Draw header
        pygame.draw.rect(screen, HEADER, (0, 0, width, 80))
        draw_text("GitHub Watcher", title_font, BACKGROUND, width // 2, 20, align="center")

        # Draw PR sections and get clickable areas
        clickable_areas, total_height = draw_pr_sections(pr_sections, scroll_y, mouse_pos)
        max_scroll = max(0, total_height - height + 100)

        # Draw scroll bar
        if total_height > height:
            scroll_height = height * (height / total_height)
            scroll_pos = (height - scroll_height) * (scroll_y / max_scroll)
            pygame.draw.rect(screen, HEADER, (width - 20, scroll_pos, 20, scroll_height))

        # Update the display
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

# Add any other UI-related functions or classes here