"""Sidebar navigation page object."""
from playwright.sync_api import Page


class Sidebar:
    def __init__(self, page: Page):
        self.page = page

    def navigate_to(self, label: str):
        """Click a sidebar nav item by its label text."""
        self.page.get_by_text(label, exact=True).click()
        self.page.wait_for_load_state("networkidle")

    def get_section_items(self, section: str) -> list[str]:
        """Get all item labels in a nav section."""
        # Find section label, then get sibling items
        section_el = self.page.locator(f"text={section}").first
        items_container = section_el.locator("..").locator("a")
        return items_container.all_text_contents()

    def is_active(self, label: str) -> bool:
        """Check if a nav item has active styling."""
        link = self.page.get_by_text(label, exact=True)
        return "active" in (link.get_attribute("class") or "")

    @property
    def all_routes(self) -> list[str]:
        return [
            "/dashboard", "/tasks", "/policies", "/results",
            "/templates", "/route-tester", "/scrape-test",
            "/amazon", "/google-maps", "/crawl", "/search",
            "/extract", "/changes", "/schedules",
            "/sessions", "/proxies", "/webhooks",
            "/mcp", "/billing",
        ]
