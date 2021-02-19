from io import StringIO
import os
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from PIL import Image
import pytesseract
from collections import OrderedDict
from datetime import datetime
import time
from lxml import etree
import json

class Scraper():

    baseurl = 'https://albop.igovsolution.net/online/Lookups/Business_Lookup.aspx'

    def __init__(self):
        self.directory = os.path.dirname(os.path.realpath(__file__))
        self.field_translator = {
            'Name': 'ENTITY_NAME_COMPANY',
            'LICENSE #': 'LICENSE_0_ID',
            'SUPERVISING PHARMACIST': '',
            'EMAIL': 'CONTACT_0_RECORD',
            'LICENSE TYPE': 'LICENSE_0_TYPE',
            'STATUS': 'LICENSE_0_STATUS',
            'ISSUED': 'LICENSE_0_BEGIN_DATE',
            'EXPIRATION': 'LICENSE_0_END_DATE',
            'Address1': 'ADDRESS_0_STREET_0',
            'Address2': 'ADDRESS_0_STREET_1',
            'City': 'ADDRESS_0_CITY',
            'State': 'ADDRESS_0_STATE',
            'Zip': 'ADDRESS_0_ZIP',
            'Discipline': 'LICENSE_0_DISCIPLINE',
        }
        self.captcha_text = ''
        self.starttime = ''
        self.xlsdirectory = ''
        self.output = []
        self.ALBOP_output = open('ALBOP_output.jsonl', 'a')


    def resetBasePage(self):
        try:
            self.driver.quit()
            print('Previous session quit.')
        except:
            pass
        finally:
            profile = webdriver.FirefoxProfile()
            profile.set_preference("browser.download.folderList", 2)
            profile.set_preference("browser.download.manager.showWhenStarting", False)
            profile.set_preference("browser.download.dir", os.getcwd() + '/' + self.xlsdirectory)
            profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/vnd.ms-excel")

            options = webdriver.FirefoxOptions()
            # options.add_argument('--headless')
            self.driver = webdriver.Firefox(options=options, firefox_profile=profile)
            self.driver.maximize_window()
            self.driver.get(self.baseurl)
            self.driver.execute_script('document.body.style.MozTransform = "scale(0.8)";')
            self.driver.execute_script('document.body.style.MozTransformOrigin = "0 0";')

    def waitclick(self, xpath):
        WebDriverWait(self.driver, 60).until(EC.visibility_of_element_located((By.XPATH, xpath)))
        self.driver.find_element_by_xpath(xpath).click()

    def solveCaptcha(self):
        raw = 'captcha-raw.png'
        fixed = 'captcha-fixed.png'
        captcha_xpath = '//img[contains(@src,"../Captcha.aspx")]'
        WebDriverWait(self.driver, 60).until(EC.visibility_of_element_located((By.XPATH, captcha_xpath)))
        self.driver.find_element_by_xpath(captcha_xpath).screenshot(raw)  # retrying can add "?rfid=0" to the captcha xpath
        print('Got raw captcha image.')
        im = Image.open(raw)
        im_resized = im.resize((im.width, int(im.height*1.5)))
        im_resized.save(fixed)
        os.remove(raw)
        self.captcha_text = pytesseract.image_to_string(Image.open(fixed)).strip()
        print('Captcha image converted to string: ' + self.captcha_text)
        os.remove(fixed)

    def search(self, county):
        self.solveCaptcha()
        self.driver.find_element_by_xpath('//input[@id="ctl00_cntbdy_txt_linum"]').clear()
        self.driver.find_element_by_xpath('//input[@id="ctl00_cntbdy_txt_linum"]').send_keys('1234567890')
        self.driver.find_element_by_xpath('//select[@id="ctl00_cntbdy_ddl_county"]').send_keys(county)
        self.driver.find_element_by_xpath('//input[@id="ctl00_cntbdy_txt_verify"]').clear()
        self.driver.find_element_by_xpath('//input[@id="ctl00_cntbdy_txt_verify"]').send_keys(self.captcha_text)
        self.driver.find_element_by_xpath('//input[@id="ctl00_cntbdy_btn_search"]').click()
        print('clicked')
        time.sleep(4)  # Time for page to load either error screen or results table. If scrape breaks, try increasing this.
        error_xpath = '//div[contains(@class,"DynamicDialogStyle")][last()]' # a new error message section is dynamically generated with each page action!
        if 'block' in self.driver.find_element_by_xpath(error_xpath).get_attribute('style'):
            self.driver.find_element_by_xpath('(//button/span[text()="Ok"])[last()]').click()  # a new "Ok" button id dynamically generated with each page action!
            raise Exception("Incorrect captcha code!")
        print('Table loaded for: ' + county)

    def latestfilecheck(self):
        paths = [self.xlsdirectory + '/' + x for x in os.listdir(self.xlsdirectory)]
        latestfile = max(paths, key=os.path.getctime)
        return latestfile

    def gatherxls(self, file):
        parser = etree.XMLParser(ns_clean=True)
        tree = etree.parse(file, parser=parser)
        root = tree.getroot()
        headers = [x.text for x in root[1][0][1]]

        for row in root[1][0][2:]:
            d = OrderedDict()
            for i,field in enumerate(row):
                d[headers[i]] = field.text
            self.ALBOP_output.write(json.dumps(d) + '\n')

        print('Records added: ' + str(len(root[1][0])))

    def run(self):
        self.starttime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.xlsdirectory = 'ALBOP_xlsresults_' + self.starttime
        os.mkdir(self.xlsdirectory)
        self.resetBasePage()
        tree = etree.parse(StringIO(self.driver.page_source), etree.HTMLParser())
        counties = tree.xpath('//select[@id="ctl00_cntbdy_ddl_county"]/option/text()')

        for county in counties[1:]:
            if len(os.listdir(self.xlsdirectory)) == 0:
                latestfile1 = ''
            else:
                latestfile1 = self.latestfilecheck()

            self.resetBasePage()

            for _ in range(0,20):
                while True:
                    try:
                        print('Retry search')
                        self.search(county)
                        break
                    except:
                        continue
                break

            xls_xpath = '//i[contains(@onclick,"generate_xls")]'
            WebDriverWait(self.driver, 60).until(EC.visibility_of_element_located((By.XPATH, xls_xpath)))
            self.driver.find_element_by_xpath(xls_xpath).click()

            for i,x in enumerate(range(0,60)):
                time.sleep(1)
                latestfile2 = self.latestfilecheck()
                if latestfile2 != latestfile1 and '.part' not in latestfile2:
                    print('Download completed: ' + county)
                    break
                else:
                    print('Downloading. Time elapsed... ' + str(i+1))

            self.gatherxls(latestfile2)


scraper = Scraper()
scraper.run()
print('Scrape completed!')