from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime

'''
Downloads all desired excel files from the website.
'''

class Scraper:
    base_url = 'https://dca.ca.gov/consumers/public_info/index.shtml'
    wantedtypes = [  # This is the name of relevant Folder Name on the base page. These are listed as examples; any folders can be chosen.
        '8500',  # Chiropractors
        '0410',  # Dental Hygiene
        '6500',  # Acupuncture
        '0800',  # Medical Board
        '0600',  # Psychology
        '0700',  # Respiratory Care
    ]

    def __init__(self):
        self.download_dir = os.getcwd()
        self.download_status = ''
        self.xlsfile = ''

    def resetdriver(self):
        try:
            self.driver.quit()
        except:
            pass
        finally:
            profile = webdriver.FirefoxProfile()
            profile.set_preference("browser.download.folderList", 2)
            profile.set_preference("browser.download.manager.showWhenStarting", False)
            profile.set_preference("browser.download.dir", self.download_dir)
            profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/vnd.ms-excel")  # See MIME types: "https://en.wikipedia.org/wiki/Media_type"

            options = webdriver.FirefoxOptions()
            options.add_argument('--headless')

            self.driver = webdriver.Firefox(firefox_profile=profile, options=options)
            self.driver.maximize_window()


    def get_BasePage(self):
        self.driver.get(self.base_url)
        WebDriverWait(self.driver, 60).until(EC.visibility_of_element_located((By.XPATH, '//*[text()="publicinfo"]')))
        print('Got base page.')

    def waitclick(self, xpath, wait=10):
        try:
            WebDriverWait(self.driver, wait).until(EC.presence_of_element_located((By.XPATH, xpath)))
            self.driver.find_element_by_xpath(xpath).click()
            print('clicked: ' + xpath)

        # If the webdriver errors out while clicking, capture a screenshot to help with debugging.
        except Exception as e:
            now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            self.driver.get_screenshot_as_file('screenshot_{}.png'.format(now))
            raise e

    def get_xls(self, licensetype):
        scrollincrements = range(0,12)
        for i,x in enumerate(scrollincrements):  # To scroll folder row into view so it's clickable
            folder_xpath = '//*[contains(text(),"{}")]'.format(licensetype)
            success = ''
            if i == len(scrollincrements)-1:
                raise Exception
            else:
                try:
                    self.waitclick(folder_xpath)
                    time.sleep(3)
                    if self.driver.find_element_by_xpath(folder_xpath).is_displayed():  # sometimes folder click doesn't work, having xls show can take a second click
                        self.waitclick(folder_xpath)
                    success = True
                    break
                except:
                    print("Didn't find folder, scrolling further down...")
                finally:
                    if not success:
                        scroll_xpath = '//div[@class="ReactVirtualized__Grid ReactVirtualized__Table__Grid"]'
                        self.driver.execute_script("arguments[0].scrollTop = {};".format((i+1)*200), self.driver.find_element_by_xpath(scroll_xpath))
                        print('times scrolled: {}'.format(i+1))

        self.waitclick('//*[contains(text(),"xls")]')
        self.waitclick('//*[contains(text(),"xls")]/parent::div/parent::div/following-sibling::div/div/button')
        self.waitclick('//*[text()="Download"]/parent::li')
        print('downloading to: ' + self.download_dir)

    def checkdownload(self, checkrepeat=120, sleeptime=5):
        if os.path.exists('geckodriver.log'):
            os.remove('geckodriver.log')
            print('geckodriver.log removed')
        for x in range(0, checkrepeat):
            time.sleep(sleeptime)
            print('Download time: ' + str((x+1)*sleeptime))

            for root, dirs, files in os.walk('.'):
                for file in files:
                    mtime = datetime.fromtimestamp(os.stat(file).st_mtime)
                    recentfile = mtime > self.starttime
                    if recentfile and file.endswith('xls') and file+'.part' not in files:
                        self.xlsfile = file
                        print('Download complete: ' + file)
                        self.driver.quit()
                        break
                if self.xlsfile:
                    break
            if self.xlsfile:
                break

            if x == len(range(0,checkrepeat))-1:
                self.driver.quit()
                Exception('Download timed out!')

    def run(self):
        self.starttime = datetime.now()
        for licensetype in self.wantedtypes:
            self.resetdriver()
            self.get_BasePage()
            self.driver.execute_script("arguments[0].scrollIntoView();", self.driver.find_element_by_xpath('//*[contains(text(),"Public Information Files")]'))  # to have the table show fully in the screen
            self.get_xls(licensetype)
            self.checkdownload()
            print('Got file: ' + licensetype)


scraper = Scraper()
scraper.run()