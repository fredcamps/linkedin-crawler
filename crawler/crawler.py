"""Core module from crawler.
"""
#!/usr/bin/env python
import argparse
import os
import sys
from abc import ABC
from typing import Dict, List
from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium.common.exceptions import StaleElementReferenceException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webelement import FirefoxWebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_HEADLESS_FLAG = '1'


class Forbidden(BaseException):
    pass


class BaseCrawler(ABC):

    PREFIX_URL = 'https://www.linkedin.com'

    def __init__(self, username: str, password: str):
        sys.setrecursionlimit(100)
        root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.headless = bool(int(os.environ.get('HEADLESS', DEFAULT_HEADLESS_FLAG)))
        self.browser = webdriver.Firefox(
            options=firefox_options,
            executable_path=os.path.join(root_path, 'geckodriver'),
        )
        self.browser.get('{}/login'.format(self.PREFIX_URL))
        username_element = self.browser.find_element_by_name('session_key')
        password_element = self.browser.find_element_by_name('session_password')
        username_element.send_keys(username)
        password_element.send_keys(password)
        submit_button = self.browser.find_element_by_xpath('//button[@type="submit"]')
        submit_button.click()
        self.authenticated = self.browser.current_url == '{}/feed/'.format(self.PREFIX_URL)

    def _validate_authentication(self):
        msg = 'Authentication Error: '
        msg += 'Try to run crawler with HEADLESS=0 and authenticate manually at LinkedIn!'
        if not self.authenticated:
            raise Forbidden(msg)

    def go_to_profile(self, slug: str):
        """Move to profile page."""
        self._validate_authentication()
        self.browser.get('{}/in/{}'.format(self.PREFIX_URL, slug))


class Parser:
    """Class that contains parsing methods.
    """

    @classmethod
    def parse_experience(cls, row_content: Tag, grouped_content: Tag = None):
        """Method that parses experience section html.
        """
        if row_content.select('.pv-entity__description'):
            description_content = row_content.select('.pv-entity__description')[0] \
                                             .get_text()

            description = " ".join(
                description_content.replace('\n', ' ')
                                   .replace('see less', ' ')
                                   .replace('  ', ' ')
                                   .split()
            )
        else:
            description = ''

        if row_content.select('.pv-entity__location'):
            location = row_content.select(
                '.pv-entity__location'
            )[0].select('span')[-1].get_text()
        else:
            location = ''

        if grouped_content:
            position = row_content.select('h3')[0] \
                                  .select('span')[-1].get_text() \
                                  .strip()
            company = grouped_content.select(
                '.pv-entity__company-summary-info'
            )[0].select('span')[1].get_text().strip()
        else:
            position = row_content.select('h3')[0].get_text().strip()
            contents = row_content.select('.pv-entity__secondary-title')[0] \
                .get_text() \
                .split()
            company = ''.join(
                [string for string in contents if 'time' not in string]
            )

        start_date = row_content.select('.pv-entity__date-range')[0] \
                                .select('span')[1] \
                                .get_text() \
                                .split('–')[0] \
                                .strip()
        end_date = row_content.select('.pv-entity__date-range')[0] \
                              .select('span')[1] \
                              .get_text() \
                              .split('–')[1] \
                              .strip()

        experience_data = {
            'company': company,
            'start_date': start_date,
            'end_date': end_date,
            'position': position,
            'location': location,
            'description': description,
        }

        return experience_data

    @classmethod
    def parse_education(cls, row_content: Tag) -> Dict:
        """Method that parses education section html.
        """
        current_item = row_content.select('.pv-entity__summary-info')[0]
        if current_item.select('.pv-entity__degree-name'):
            degree = current_item.select('.pv-entity__degree-name')[0] \
                                 .select('.pv-entity__comma-item')[0] \
                                 .get_text()
        else:
            degree = ''

        if current_item.select('.pv-entity__fos'):
            field_of_study = current_item.select('.pv-entity__fos')[0] \
                .select('span')[-1] \
                .get_text()
        else:
            field_of_study = ''

        if current_item.select('.pv-entity__school-name'):
            school = current_item.select('.pv-entity__school-name')[0] \
                                 .get_text()
        else:
            school = ''

        if current_item.select('.pv-entity__dates')[0]:
            start_date = current_item.select('.pv-entity__dates')[0].select('time')[0].get_text()
            end_date = current_item.select('.pv-entity__dates')[0].select('time')[1].get_text()

        return {
            'school': school,
            'field_of_study': field_of_study,
            'degree': degree,
            'start_date': start_date,
            'end_date': end_date,
        }

    @classmethod
    def parse_certification(cls, row_content: Tag) -> Dict:
        """Method that parses certification content html."""
        current_item = row_content.select('.pv-certifications__summary-info')[0]
        if current_item.select('span'):
            company = current_item.select('span')[1].get_text()
            issue_date = '' if len(current_item) <= 3 else current_item.select('span')[3].get_text()
            due_date = '' if len(current_item) <= 4 else current_item.select('span')[4].get_text()
            credential = '' if len(current_item) <= 5 else current_item.select('span')[5].get_text()
        else:
            company = ''
            issue_date = ''
            due_date = ''
            credential = ''

        if current_item.select('h3'):
            title = current_item.select('h3')[0].get_text()
        else:
            title = ''

        return {
            'company': company,
            'title': title,
            'issue_date': issue_date,
            'due_date': due_date,
            'credential': credential,
        }

    @classmethod
    def parse_about(cls, row_content: Tag) -> str:
        """Method that parses about section html."""
        return " ".join(row_content.get_text()
                                   .replace('\n', ' ')
                                   .replace('  ', ' ')
                                   .split())


class Crawler(BaseCrawler):
    """Class that represents crawler.
    """

    @classmethod
    def _get_section_elements(cls, selector: str, method: callable):
        html_section = method()
        soup = BeautifulSoup(html_section, 'lxml')
        rows = soup.select('html')
        return rows

    def _expand_items(self, section: FirefoxWebElement, element_class: str):
        elements = section.find_elements_by_class_name(element_class)
        for element in elements:
            try:
                if element.get_attribute('aria-expanded') != 'true' and EC.element_to_be_clickable(
                    element
                ):
                    element.click()
            except StaleElementReferenceException:
                continue

        try:
            self._expand_items(section, element_class)
        except RecursionError:
            return

    def _fetch_elements_by_class(self, class_name: str) -> FirefoxWebElement:
        WebDriverWait(self.browser, 1).until(
            EC.presence_of_element_located((By.CLASS_NAME, class_name))
        )
        section = self.browser.find_elements_by_class_name(class_name)

        return section

    def _fetch_arbitrary_section_html(
        self,
        class_name,
        item_expander_class='pv-profile-section__see-more-inline',
    ) -> FirefoxWebElement:
        sections = self._fetch_elements_by_class(
            class_name=class_name
        )
        if sections:
            section = sections[0]
        else:
            section = None
        self._expand_items(section=section, element_class=item_expander_class)
        return section.get_attribute('innerHTML')

    def _fetch_about_section_html(self) -> FirefoxWebElement:
        return self._fetch_arbitrary_section_html(
            class_name='pv-about-section',
            item_expander_class='lt-line-clamp__more',
        )

    def _fetch_education_section_html(self) -> FirefoxWebElement:
        return self._fetch_arbitrary_section_html(class_name='education-section')

    def _fetch_certification_section_html(self) -> FirefoxWebElement:
        return self._fetch_arbitrary_section_html(class_name='certification-section')

    def _fetch_experiences_section_html(self) -> FirefoxWebElement:
        experience_section_class = 'experience-section'
        experience_section = self._fetch_elements_by_class(
            class_name=experience_section_class
        )[0]
        self._expand_items(
            section=experience_section,
            element_class='inline-show-more-text__button'
        )
        self._expand_items(
            section=experience_section,
            element_class='pv-profile-section__see-more-inline'
        )

        return experience_section.get_attribute('innerHTML')

    def _fetch_arbitrary_data(
        self,
        section_method: callable,
        parser_method: callable,
        selector: str,
    ):
        elements = self._get_section_elements(
            method=section_method,
            selector=selector,
        )[0]
        if not isinstance(elements, list):
            return [parser_method(elements)]

        items = []
        for item in elements:
            items.append(parser_method(item))

        return items

    def fetch_about_data(self) -> str:
        """Fetch data from about section.
        """
        self._validate_authentication()
        return self._fetch_arbitrary_data(
            section_method=self._fetch_about_section_html,
            parser_method=Parser.parse_about,
            selector='.pv-about-section'
        )

    def fetch_experience_data(self) -> List[Dict]:
        """Fetch data from experience section.
        """
        self._validate_authentication()
        experiences = []
        elements = self._get_section_elements(
            method=self._fetch_experiences_section_html,
            selector='.experience-section',
        )[0]
        for row in elements:
            if row.select('.pv-entity__company-summary-info'):
                for row_detail in row.select('.pv-entity__role-details'):
                    experiences.append(
                        Parser.parse_experience(row_detail, row)
                    )
            if row.select('.pv-entity__secondary-title'):
                experiences.append(Parser.parse_experience(row))

        return experiences

    def fetch_education_data(self) -> List[Dict]:
        """Fetch data from education section.
        """
        self._validate_authentication()
        return self._fetch_arbitrary_data(
            section_method=self._fetch_education_section_html,
            parser_method=Parser.parse_education,
            selector='.education-section',
        )

    def fetch_certification_data(self) -> List[Dict]:
        """Fetch data from certification section.
        """
        self._validate_authentication()
        return self._fetch_arbitrary_data(
            section_method=self._fetch_certification_section_html,
            parser_method=Parser.parse_certification,
            selector='.certification-section',
        )

    def fetch_skills_data(self) -> List[str]:
        """Fetch data from skills elements.
        """
        self._validate_authentication()
        skills_tag_class = "pv-skill-category-entity__name-text"
        elements = self._fetch_elements_by_class(
            class_name=skills_tag_class
        )
        skills = []
        for skill in elements:
            skills.append(skill.text)

        return skills


def run():
    """Run Crawler."""
    crawler = Crawler(
        username=os.environ.get('EMAIL'),
        password=os.environ.get('PASSWORD'),
    )
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', help='Profile slug on url suffix. e.g maccabelli')
    args = parser.parse_args()
    crawler.go_to_profile(slug=args.profile)
    data = {
        # 'about': crawler.fetch_about_data(),
        # 'education': crawler.fetch_education_data(),
        # 'certifications': crawler.fetch_certification_data(),
        # 'skills': crawler.fetch_skills_data(),
        'experiences': crawler.fetch_experience_data(),
    }
    return data


def main():
    """Driver function."""
    data = run()
    print(data)


if __name__ == '__main__':
    main()
