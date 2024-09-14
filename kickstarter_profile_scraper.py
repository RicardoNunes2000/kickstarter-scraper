from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import json
import logging


class ProjectInfo(BaseModel):
    title: str
    status: str
    percent_funded: Optional[int] = None
    categories: List[str]
    project_url: HttpUrl


class Creator(BaseModel):
    creatorUrl: Optional[HttpUrl]
    creatorName: Optional[str]
    creatorState: Optional[str]
    creatorCity: Optional[str]
    creatorJoined: Optional[datetime]
    creatorBackerFavorite: Optional[bool]
    creatorSuperbacker: Optional[bool]
    creatorAbout: Optional[str] = None
    creatorWebsites: Optional[List[HttpUrl]] = None
    creatorProjects: Optional[List[ProjectInfo]] = None
    backedProjects: Optional[int]
    creatorCreatedProjects: Optional[int]


class KickstarterScraper:
    def __init__(self):
        self.base_url = (
            "https://www.kickstarter.com/profile/{username_id}?page={page_id}"
        )
        self.created_projects_url = (
            "https://www.kickstarter.com/profile/{username_id}/created?page={page_id}"
        )

        self.session = requests.Session()
        logging.basicConfig(level=logging.INFO)

    def get_creator_info(self, username_id: str) -> Creator:
        """Fetches and returns creator information."""
        try:
            url = self.base_url.format(username_id=username_id, page_id=1)
            response = self.session.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Error fetching creator info: {e}")
            return Creator()

        soup = BeautifulSoup(response.text, "html.parser")
        profile_bio = soup.find("div", class_="profile_bio")

        creator = Creator(
            creatorUrl=url,
            creatorName=self._get_creator_name(profile_bio),
            creatorCity=self._get_creator_location(profile_bio, "city"),
            creatorState=self._get_creator_location(profile_bio, "state"),
            creatorJoined=self._get_creator_joined_date(profile_bio),
            creatorBackerFavorite=self._is_backer_favorite(profile_bio),
            creatorSuperbacker=self._is_superbacker(profile_bio),
            backedProjects=self._get_backed_projects_count(profile_bio),
            creatorProjects=self._get_creator_projects_info(username_id),
            creatorCreatedProjects=self._get_creator_created_projects_count(soup),
            creatorAbout=self._get_creator_description(soup),
        )

        return creator

    def _get_creator_name(self, profile_bio):
        """Extracts the creator's name from the profile bio."""
        name_tag = profile_bio.find("h2", class_="mb2")
        return name_tag.text.strip() if name_tag else None

    def _get_creator_location(self, profile_bio, location_type):
        """Extracts the creator's city or state from the profile bio."""
        location_tag = profile_bio.find("span", class_="location")
        if location_tag:
            location_text = location_tag.find("a").text.strip()
            return self._parse_location(location_text, location_type)
        return None

    def _parse_location(self, location_text, location_type):
        """Parses the location text into city and state components."""
        location_parts = location_text.split(", ")
        if location_type == "city":
            return location_parts[0] if len(location_parts) > 0 else None
        elif location_type == "state":
            return location_parts[1] if len(location_parts) > 1 else None
        return None

    def _get_creator_joined_date(self, profile_bio):
        """Extracts the date the creator joined Kickstarter."""
        joined_tag = profile_bio.find("span", class_="joined")
        if joined_tag:
            time_tag = joined_tag.find("time")
            if time_tag and "datetime" in time_tag.attrs:
                return datetime.strptime(time_tag["datetime"], "%Y-%m-%dT%H:%M:%S%z")
        return None

    def _is_backer_favorite(self, profile_bio):
        """Determines if the creator has the 'Backer Favorite' badge."""
        badges = profile_bio.find("div", {"data-badges": True})
        if badges and badges["data-badges"]:
            badge_list = json.loads(badges["data-badges"])
            return "backer-favorite" in badge_list
        return False

    def _is_superbacker(self, profile_bio):
        """Determines if the creator has the 'Superbacker' badge."""
        badges = profile_bio.find("div", {"data-badges": True})
        if badges and badges["data-badges"]:
            badge_list = json.loads(badges["data-badges"])
            return "superbacker" in badge_list
        return False

    def _get_backed_projects_count(self, profile_bio):
        """Extracts the number of projects the creator has backed."""
        backed_tag = profile_bio.find("span", class_="backed")
        if backed_tag:
            match = re.search(r"Backed (\d+) projects", backed_tag.text)
            return int(match.group(1)) if match else 0
        return 0

    def _get_creator_description(self, soup):
        """Extracts the creator's description from the meta tag."""
        meta_tag = soup.find("meta", property="og:description")
        return meta_tag["content"] if meta_tag and "content" in meta_tag.attrs else None

    def _get_creator_created_projects_count(self, soup):
        """Extracts the number of projects the creator has launched from the new field."""
        created_tag = soup.find("a", id="profile_created")
        if created_tag:
            count_tag = created_tag.find("span", class_="count")
            if count_tag:
                return int(count_tag.text.strip())
        return 0

    def _get_creator_projects_info(self, username_id: str) -> List[ProjectInfo]:
        """Extracts information about each project the creator has launched."""
        projects = []
        url = self.created_projects_url.format(username_id=username_id, page_id=1)
        try:
            response = self.session.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Error fetching creator projects: {e}")
            return projects

        soup = BeautifulSoup(response.text, "html.parser")
        projects_div = soup.find("div", {"data-projects": True})

        if projects_div:
            json_data = projects_div["data-projects"]
            projects_data = json.loads(json_data)

            for project in projects_data:
                title = project.get("name", "Unknown")
                status = project.get("state", "Unknown")
                pledged = project.get("pledged", 0)
                goal = project.get("goal", 0)

                percent_funded = None
                if goal > 0:
                    percent_funded = int((pledged / goal) * 100)

                categories = [
                    category.get("name", "Unknown")
                    for category in project.get("category", {}).get("parents", [])
                ]
                project_url = (
                    f"https://www.kickstarter.com/projects/{project.get('slug', '')}"
                )

                project_info = ProjectInfo(
                    title=title,
                    status=status,
                    percent_funded=percent_funded,
                    categories=categories,
                    project_url=project_url,
                )

                projects.append(project_info)

        return projects

if __name__ == "__main__":
    scraper = KickstarterScraper()
    sample_creator = "worthychaoscomics"

    creator_info = scraper.get_creator_info(sample_creator)
    print(creator_info)
