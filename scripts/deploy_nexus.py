#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import argparse
import logging
import os
import re
import subprocess
import tempfile
import textwrap
import time
import urllib2
import zipfile
from contextlib import closing, contextmanager

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait

import utils

LOGGER = logging.getLogger(__name__)

COOKIES_TEMPLATE = {
    "domain": ".nexusmods.com",
    "expires": None,
    "httpOnly": False,
    "name": None,
    "path": "/",
    "secure": True,
    "value": None,
}
ID_DICT = {
    # oblivion
    101: 22368,
    # skyrim
    110: 1840,
    # skyrim special edition
    1704: 6837,
    # fallout 3
    120: 22934,
    # fallout new vegas
    130: 64580,
    # fallout 4
    1151: 20032,
    # enderal
    2736: 97,
}
DESC_DICT = {
    "Installer": (
        "Executable automated Installer. This will by "
        "default install just the Standalone Wrye Bash. "
        "It can also install all requirements for a full "
        "Python setup if you have any plans to join in "
        "with development."
    ),
    "Python Source": (
        "This is a manual installation of Wrye Bash Python files, requiring "
        "the full Python setup files to also be manually installed first."
    ),
    "Standalone Executable": (
        "This is a manual installation of the Wrye Bash Standalone files."
    ),
}
DESC_ADDON = (
    " This is the latest development version fixing many bugs and "
    "adding new features - use this in preference to the main files."
)
CATEGORY = {"nightly": "Updates", "production": "Main Files"}
REGEX = {
    "nightly": re.compile(
        r"Wrye Bash (\d{3,}\.\d{12,12}) - (?:Installer|Python Source|Standalone Executable)"
    ),
    "production": re.compile(
        r"Wrye Bash (\d{3,})(?: (\w+) (\d+))? - (?:Installer|Python Source|Standalone Executable)"
    ),
}
SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
BUILD_PATH = os.path.join(SCRIPTS_PATH, "build")
CHROMEDRIVER_PATH = os.path.join(utils.DEPLOY_FOLDER, "chromedriver.exe")


def remove_cookie_overlay(driver):
    # selenium can't seem to find the overlay element
    # so we just wait a bit for it to load properly
    time.sleep(2)
    # hide the overlay
    driver.execute_script("$('.qc-cmp-showing').css('visibility', 'hidden');")
    # "unlock" the actual webpage
    driver.execute_script("$('.qc-cmp-ui-showing').removeClass('qc-cmp-ui-showing');")


class Chrome(webdriver.Chrome):
    def get(self, url, *args, **kwargs):
        super(Chrome, self).get(url, *args, **kwargs)
        remove_cookie_overlay(self)


# https://blog.codeship.com/get-selenium-to-wait-for-page-load/
@contextmanager
def wait_for_page_load(browser, timeout=30):
    old_page = browser.find_element_by_tag_name("html")
    yield
    WebDriverWait(browser, timeout).until(ec.staleness_of(old_page))
    remove_cookie_overlay(browser)


def setup_parser(parser):
    parser.add_argument(
        "-m",
        "--member-id",
        default=argparse.SUPPRESS,
        help="The 'value' from the cookie 'member_id' in the domain 'nexusmods.com'",
    )
    parser.add_argument(
        "-p",
        "--pass-hash",
        default=argparse.SUPPRESS,
        help="The 'value' from the cookie 'pass_hash' in the domain 'nexusmods.com'",
    )
    parser.add_argument(
        "-s",
        "--sid",
        default=argparse.SUPPRESS,
        help="The 'value' from the cookie 'sid' in the domain 'nexusmods.com'",
    )
    parser.add_argument(
        "-d",
        "--driver-version",
        default=None,
        help="Provide a version to override the current chromedriver.",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run with a fully visible browser. Useful for debugging.",
    )
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument(
        "--nightly",
        action="store_const",
        const="nightly",
        dest="release",
        help="Deploy as nightly release to 'Updates' category [default].",
    )
    version_group.add_argument(
        "--production",
        action="store_const",
        const="production",
        dest="release",
        help="Deploy as production release to 'Main Files' category.",
    )
    parser.set_defaults(release="nightly")


def install_chromedriver(version_override=None):
    if version_override is None:
        reg_string = subprocess.check_output(
            'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version'
        )
        chrome_version = reg_string.strip().split()[-1]
        LOGGER.debug("Found chrome browser, version {}".format(chrome_version))
        driver_version_base_url = (
            "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_"
        )
        response = urllib2.urlopen(
            driver_version_base_url + chrome_version.rsplit(".")[0]
        )
        driver_version = response.read()
        if os.path.isfile(CHROMEDRIVER_PATH):
            existing_version = subprocess.check_output(
                [CHROMEDRIVER_PATH, "--version"]
            ).split()[1]
            LOGGER.debug(
                "Found existing local chromedriver, version {}".format(existing_version)
            )
            if driver_version == existing_version:
                LOGGER.debug(
                    "Local chromedriver is up-to-date [version {}]".format(
                        driver_version
                    )
                )
                return
    else:
        LOGGER.debug(
            "Overriding chromedriver version with {}...".format(version_override)
        )
        driver_version = version_override
    driver_base_url = (
        "https://chromedriver.storage.googleapis.com/{}/chromedriver_win32.zip"
    )
    download_dir = tempfile.mkdtemp()
    archive_path = os.path.join(download_dir, "chromedriver_win32.zip")
    LOGGER.info("Downloading chromedriver {}...".format(driver_version))
    utils.download_file(driver_base_url.format(driver_version), archive_path)
    utils.mkdir(utils.DEPLOY_FOLDER)
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        zip_ref.extractall(utils.DEPLOY_FOLDER)
    os.remove(archive_path)
    os.rmdir(download_dir)


def setup_driver(headless=True):
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--log-level=3")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    if headless:
        options.add_argument("--disable-gpu")
        options.add_argument("--headless")
    driver = Chrome(CHROMEDRIVER_PATH, chrome_options=options)
    LOGGER.debug("Successfully created a new chrome driver")
    return driver


def load_cookies(driver, creds):
    cookies = []
    for name, value in creds.iteritems():
        cookie = dict(COOKIES_TEMPLATE)
        cookie["name"] = name
        cookie["value"] = value
        cookies.append(cookie)
    driver.get("https://www.nexusmods.com")
    for cookie in cookies:
        driver.add_cookie(cookie)


def remove_files(driver, release, dry_run=False):
    xpath = "//div[@class='file-category']/h3[text()='{}']/../ol/li".format(
        CATEGORY[release]
    )
    file_entries = driver.find_elements_by_xpath(xpath)
    for entry in file_entries:
        fname_xpath = "div[@class='file-head']/h4"
        fname = entry.find_element_by_xpath(fname_xpath).text
        LOGGER.debug("Checking file '{}'...".format(fname))
        if REGEX[release].match(fname) is None:
            continue
        LOGGER.debug("File '{}' has matched.".format(fname))
        if dry_run:
            LOGGER.info("Would delete file '{}'...".format(fname))
            continue
        delete_xpath = (
            "div[@class='file-body']/ul/li[@class='drop-down']"
            "/div[@class='subnav']/ul/li/a[@class='delete-file']"
        )
        delete_button = entry.find_element_by_xpath(delete_xpath)
        file_id = delete_button.get_attribute("data-file-id")
        js_query = "document.querySelector('[data-file-id=\"{}\"]').click();".format(
            file_id
        )
        driver.execute_script(js_query)
        driver.switch_to_alert().accept()
        LOGGER.info("Deleted file '{}'".format(fname))
    # nexus needs time to refresh after deleting everything
    time.sleep(5)


def upload_file(driver, fpath, release, dry_run=False):
    fname = os.path.basename(fpath)
    name = os.path.splitext(fname)[0]
    match = re.match(REGEX[release], name)
    version = match.group(1)
    if release == "production":
        stage, stage_num = match.group(2, 3)
        if stage is not None:
            version += "." + stage.lower() + stage_num
    # mod name
    mod_name_elem = driver.find_element_by_name("name")
    mod_name_elem.send_keys(name)
    actual_name = mod_name_elem.get_attribute("value")
    LOGGER.info("File name: '{}'".format(actual_name))
    assert actual_name == name, "Mod name was not correctly set. Expected: " + name
    # mod version
    mod_version_elem = driver.find_element_by_name("file-version")
    mod_version_elem.send_keys(version)
    actual_version = mod_version_elem.get_attribute("value")
    LOGGER.info("File version: '{}'".format(actual_version))
    assert actual_version == version, (
        "Mod version was not correctly set. Expected: " + version
    )
    # mod category
    category_select = Select(driver.find_element_by_id("select-file-category"))
    category_select.select_by_visible_text(CATEGORY[release])
    actual_category = category_select.first_selected_option.text
    LOGGER.info("File category: '{}'".format(actual_category))
    assert actual_category == CATEGORY[release], (
        "Mod category was not correctly selected. Expected: " + CATEGORY[release]
    )
    # mod description
    mod_desc = next(value for key, value in DESC_DICT.iteritems() if key in name)
    if release == "nightly":
        mod_desc += DESC_ADDON
    mod_desc_elem = driver.find_element_by_id("file-description")
    mod_desc_elem.send_keys(mod_desc)
    actual_desc = mod_desc_elem.get_attribute("value")
    LOGGER.info("File description:")
    LOGGER.info(textwrap.fill(actual_desc, initial_indent="  ", subsequent_indent="  "))
    assert actual_desc == mod_desc, (
        "Mod description was not correctly set. Expected:\n"
        + textwrap.fill(mod_desc, initial_indent="  ", subsequent_indent="  ")
    )
    # remove download with manager button
    driver.find_element_by_id("option-dlbutton").click()
    # upload the actual file
    if dry_run:
        LOGGER.info(
            "Would upload file '{}'.".format(os.path.relpath(fpath, os.getcwd()))
        )
        with wait_for_page_load(driver):
            driver.refresh()
            driver.switch_to_alert().accept()
        return
    LOGGER.info("Uploading file '{}'...".format(os.path.relpath(fpath, os.getcwd())))
    driver.find_element_by_xpath("//input[@type='file']").send_keys(fpath)
    # Will wait 1 hour for file upload - no point in doing timeouts if goal is ci
    WebDriverWait(driver, 3600).until(
        ec.text_to_be_present_in_element(
            (By.XPATH, "//div[@id='upload_success']"), fname + " has been uploaded."
        )
    )
    LOGGER.debug("Upload finished.")
    # page will auto refresh after "saving" the new file
    with wait_for_page_load(driver):
        driver.find_element_by_xpath(
            "//button[@class='btn inline mod-add-file']"
        ).click()


def main(args):
    utils.setup_log(LOGGER, verbosity=args.verbosity, logfile=args.logfile)
    creds = utils.parse_deploy_credentials(
        args, ["member_id", "pass_hash", "sid"], args.save_config
    )
    install_chromedriver(args.driver_version)
    driver = setup_driver(args.headless)
    driver.maximize_window()
    load_cookies(driver, creds)
    with closing(driver):
        for game_id, mod_id in ID_DICT.iteritems():
            driver.get(
                "https://www.nexusmods.com/mods/edit/?step=files"
                "&id={}&game_id={}".format(mod_id, game_id)
            )
            LOGGER.info("Deleting old files for game {}.".format(game_id))
            remove_files(driver, args.release, args.dry_run)
            LOGGER.info("Uploading new files for game {}.".format(game_id))
            for fname in os.listdir(args.dist_folder):
                fpath = os.path.join(args.dist_folder, fname)
                if not os.path.isfile(fpath):
                    continue
                upload_file(driver, fpath, args.release, args.dry_run)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    utils.setup_deploy_parser(argparser)
    setup_parser(argparser)
    parsed_args = argparser.parse_args()
    open(parsed_args.logfile, "w").close()
    main(parsed_args)
