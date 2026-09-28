from __future__ import annotations
from urllib.parse import urljoin
from ..processing.html_parser import parse_list_page,has_next_page

class PortalAdapter:
    def __init__(self, config:dict):self.config=config
    def parse_list(self, html:str, url:str):return parse_list_page(html,url,self.config)
    def next_url(self, html:str, url:str) -> str|None:
        from bs4 import BeautifulSoup
        if not has_next_page(html,self.config):return None
        el=BeautifulSoup(html,"html.parser").select_one(self.config["next_button_selector"])
        return urljoin(url,el.get("href")) if el and el.get("href") else None
