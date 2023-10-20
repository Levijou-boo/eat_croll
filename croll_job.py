# %%
from collections import OrderedDict
import os
import calendar
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
import time
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from pprint import pprint
import re
from pymongo import MongoClient
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

input_element = ['mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_baseInfo1.form.div_sub6.form.edt_opngDt:input',
                 'mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_baseInfo1.form.div_sub3.form.edt_bgngPrc:input',
                 'mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_baseInfo1.form.div_sub1.form.edt_cnptNm:input',
                 'mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_baseInfo1.form.div_sub9SucbidDcsnMth1.form.edt_sucbidDcsnMthCd:input',
                 'mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_baseInfo1.form.div_sub5.form.edt_elctrnBidPlnprc_00:input',
                 'mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_baseInfo1.form.div_sub1.form.edt_bidNm:input'
                 ]


# 주소 분리
def split_address(address_str):
    if not address_str:
        return None

    try:
        tokens = address_str.split()

        data = {}

        # 도/특별시/광역시
        data['도/특별시/광역시'] = tokens[0]

        # 시/군/구
        if '시' in tokens[1] or '군' in tokens[1] or '구' in tokens[1]:
            data['시/군/구'] = tokens[1]
            start_index = 2
        else:
            data['시/군/구'] = ""
            start_index = 1

        # 읍/면/동/도로명 및 번지/상세주소
        data['읍/면/동/도로명'] = ' '.join(tokens[start_index:-1])  # 마지막 항목 전까지
        data['번지/상세주소'] = tokens[-1]  # 마지막 항목

        return data
    except Exception as e:
        print(f"Error processing address: {address_str}. Error: {e}")
        return None

# Element 값을 안전하게 가져오는 함수


def safe_find_element_by_id(driver_instance, id, skip_numeric_conversion=False):
    try:
        element = driver_instance.find_element(By.ID, id)
        text = element.text if element.text else element.get_attribute('value')

        if not skip_numeric_conversion:
            if ',' in text and '%' not in text:
                return int(text.replace(',', ''))

            # 입력된 값이 '투찰율' 형식인 경우
            elif '%' in text:
                return float(text.replace('%', '')) / 100

        # 그 외의 경우 혹은 skip_numeric_conversion이 True인 경우
        return text

    except:
        return None


# 문자열에서 숫자만 추출하는 함수

def extract_numbers_from_string(s):
    try:
        return int(''.join(re.findall(r'\d', s)))
    except:
        return None


def string_to_datetime(date_string):
    try:
        return datetime.strptime(date_string, "%Y-%m-%d %H시%M분")
    except:
        return None


def close_new_tabs(driver):
    tabs = driver.window_handles
    while len(tabs) != 2:
        driver.switch_to.window(tabs[1])
        driver.close()
        tabs = driver.window_handles
    driver.switch_to.window(tabs[0])


def wait_for_new_tab(driver, timeout=10):
    WebDriverWait(driver, timeout).until(lambda d: len(d.window_handles) > 1)


def extract_bid_data(driver_instance):
    data = []
    row_idx = 0
    while row_idx < 5:
        try:
            company_name = safe_find_element_by_id(
                driver_instance, f"mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_sub14bidStus2.form.grd_bidList2.body.gridrow_{row_idx}.cell_{row_idx}_4:text")
            rank = safe_find_element_by_id(
                driver_instance, f"mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_sub14bidStus2.form.grd_bidList2.body.gridrow_{row_idx}.cell_{row_idx}_1:text")
            bid_amount = safe_find_element_by_id(
                driver_instance, f"mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_sub14bidStus2.form.grd_bidList2.body.gridrow_{row_idx}.cell_{row_idx}_5:text")
            bid_rate = safe_find_element_by_id(
                driver_instance, f"mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_sub14bidStus2.form.grd_bidList2.body.gridrow_{row_idx}.cell_{row_idx}_7:text")

            data.append({
                "업체명": company_name,
                "순위": rank,
                "입찰금액": bid_amount,
                "투찰율": bid_rate
            })
            row_idx += 1
        except:
            # 더 이상의 행이 없을 때 반복문 종료
            break
    return data


# 연도별 날짜 반환


def get_month_start_end_dates_with_calendar(year, start_month=1):
    year = int(year)

    # 각 월의 시작 및 종료 날짜를 저장하는 리스트
    month_dates = []

    for month in range(start_month, 13):  # start_month부터 12월까지 반복
        # 해당 월의 첫째 날
        first_date = datetime(year, month, 1).strftime('%Y-%m-%d')

        # 해당 월의 마지막 날 (calendar.monthrange() 사용)
        _, last_day = calendar.monthrange(year, month)
        last_date = datetime(year, month, last_day).strftime('%Y-%m-%d')

        month_dates.append((first_date, last_date))

    return month_dates


def fetch_and_process_data(driver_instance):
    result = OrderedDict()  # 순서가 보장된 딕셔너리 생성

    mapping_keys = [
        "날짜",
        "기초가격",
        "발주처",
        "낙찰방식",
        "낙찰예정가격",
        "공고건명"
    ]

    for idx, input_id in enumerate(input_element):
        value = safe_find_element_by_id(
            driver_instance, input_id, skip_numeric_conversion=True)

        if idx == 0:
            value = string_to_datetime(value)

        if idx in [1, 3, 4]:
            value = extract_numbers_from_string(value)

        result[mapping_keys[idx]] = value

    local = safe_find_element_by_id(
        driver_instance, 'mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_baseInfo1.form.div_sub1.form.edt_dogAddr:input')
    result['지역'] = split_address(local)
    result["낙찰업체"] = extract_bid_data(driver_instance)
    return result


def try_get_detail_element():
    """상세페이지 찾을 수 없으면 True 반환

        찾을 시 False
    Returns:
        _type_: bool
    """
    try:
        # 10초 동안 해당 요소가 나타날 때까지 기다립니다.
        element = WebDriverWait(driver_instance, 10).until(
            EC.presence_of_element_located(
                (By.ID, 'mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8061000.form.div_work.form.div_main.form.div_baseInfo1.form.div_sub1.form.sta_ctrtMthCd'))
        )
        return False
    except NoSuchElementException:
        print('try_get_detail_element 상세페이지 error')
        return True


def next_button_click(currunt_count):
    wait = WebDriverWait(driver_instance, 20)
    next_button = driver_instance.find_element(
        By.CSS_SELECTOR, '#mainframe\\.VFS_MAIN\\.HFS_MAIN\\.VFS_WORK\\.FS_WORK\\.win8060300\\.form\\.div_work\\.form\\.div_page01\\.form\\.div_pagingNo\\.form\\.btn_next')
    for _ in range(currunt_count):

        wait.until(EC.invisibility_of_element_located(
            (By.ID, 'mainframe.waitwindow')))
        next_button.click()


class document_is_complete(object):
    """An expectation for checking that the document is in complete state."""

    def __call__(self, driver):
        return driver.execute_script("return document.readyState") == "complete"


class CustomFirefoxDriver():
    def __init__(self, url):
        self.url = url
        # self.profile_path = r'C:\Users\kano\AppData\Roaming\Mozilla\Firefox\Profiles\s8543x41.default-release'
        self.options = self.configure_options()
        self.service = Service('./geckodriver.exe')
        self.driver = self.configure_driver()
        self.run_driver()

    def quit(self):
        self.driver.quit()
        
    def configure_options(self):
        options = Options()
        options.add_argument('--headless')
        # options.set_preference('profile', self.profile_path)
        options.set_preference("dom.popup_maximum", 0)
        return options

    # firefox driver 설정 반환, keep_alive=True로 설정
    def configure_driver(self):
        return webdriver.Firefox(options=self.options, service=self.service, keep_alive=True)

    # 드라이버 실행
    def run_driver(self):
        self.driver.get(self.url)
        self.driver.set_window_size(6144, 3456)
        import pyautogui
        time.sleep(5)
        self.driver.switch_to.window(self.driver.current_window_handle)
        # pyautogui.keyDown('ctrl')

        # for _ in range(7):
        #         pyautogui.press('-')
        #         time.sleep(1)
        # pyautogui.keyUp('ctrl')

    def get_webdriver_instance(self):
        return self.driver
    # 요소를 찾을 때까지 기다린 후 클릭

    def waite_and_click(self, id, timeout=10):
        try:
            # Wait for the page to load completely
            WebDriverWait(self.driver, timeout).until(document_is_complete())

            # Wait for the element to be clickable and then click
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.ID, id)))
            element.click()
        except:
            print(f"{id}요소를 찾는데 너무 오래 걸렸습니다.")

    # 텍스트 입력
    def wait_input_text(self, id, text, timeout=10):
        try:
            # input 태그 선택
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, id)))
            element.clear()
            # 텍스트 입력
            element.send_keys(text)
        except:
            print(f"{id}요소를 찾는데 너무 오래 걸렸습니다.")

    def input_text(self, id, text, timeout=10):
        element = driver_instance.find_element(By.ID, id)
        element.clear()
        element.click()
        element.send_keys(text)

    def click_element_by_css(self, selector, timeout=10):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            element.click()
        except:
            print(f"{selector} 요소를 찾는데 너무 오래 걸렸습니다.")

    def click_element_by_xpath(self, xpath, timeout=10):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
            element.click()
        except:
            print(f"{xpath} 요소를 찾는데 너무 오래 걸렸습니다.")

    def find_element_by_id(self, id, timeout=10):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, id)))
            return element
        except:
            print(f"{id} 요소를 찾는데 너무 오래 걸렸습니다.")

    def wait_for_elements_by_xpath(self, xpath, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_all_elements_located((By.XPATH, xpath)))

    def wait_until_element_disappears(self, locator, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(locator))
        except TimeoutException:
            print("Element did not disappear in the expected time.")

    def wait_until_element_appears(self, locator, timeout=10):
        try:
            return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            print("Element did not appear in the expected time.")

    def go_into_and_exit_detail_page(self, xpath):
        try:
            wait = WebDriverWait(self.driver, 10)

            # 상세페이지 진입
            details = self.wait_for_elements_by_xpath(xpath)
            for detail in details:
                # 웹 요소가 완전히 나타날 때까지 기다리고 클릭
                clickable_element = self.wait_until_element_appears(
                    (By.XPATH, xpath))
                clickable_element.click()
                # 상세페이지 나가기
                exit_locator = (
                    By.XPATH, '//*[@id="mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.CF_MDI.form.div_mdi.form.btn_mdiClosewin8061000"]')
                exit_button = self.wait_until_element_appears(exit_locator)
                exit_button.click()

                # 상세 페이지가 완전히 사라질 때까지 대기
                self.wait_until_element_disappears(exit_locator)
        except NoSuchElementException:
            pass
        except ElementNotInteractableException:
            print('Detail page not accessible')
            pass

    def check_element_status(self, selector):
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        return element.get_attribute('status')


def insert_data_if_not_exists(data: OrderedDict) -> None:
    """
    주어진 데이터를 MongoDB에 삽입합니다.
    '날짜', '기초가격', '발주처', '공고건명' 필드가 모두 중복되지 않을 경우에만 삽입합니다.
    """
    existing_document = collection.find_one({
        '날짜': data['날짜'],
        '기초가격': data['기초가격'],
        '발주처': data['발주처'],
        '공고건명': data['공고건명']
    })

    if not existing_document:
        result = collection.insert_one(data)
    else:
        pass


uri = "mongodb+srv://mafumafu9854:3eWoSwhmDvhlim9L@cluster0.nxdfqvk.mongodb.net/?retryWrites=true&w=majority"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = client['eat_croll']
collection = db['eat_croll_data']

# 사용 예:
url = 'https://ns.eat.co.kr/NeaT/eats/index.html'
firefox = CustomFirefoxDriver(url)
driver_instance = firefox.get_webdriver_instance()


# %%
# 검색
def move_targe_page(firefox, start_year, end_year, notice_title, retries=3):
    if retries <= 0:
        print("Failed after multiple retries.")
        return
    try:
        driver_instance.refresh()
        # 페이지가 완전히 로드될 때까지 대기 (예: 10초 동안 특정 요소가 로드되기를 기다림)
        # element_present = EC.presence_of_element_located((By.ID, 'mainframe.VFS_MAIN.HFS_MAIN.CF_LEFT.form.btn_8000000:icontext')) # 여기서 'some_element_id_to_check'는 로드를 확인할 요소의 ID입니다.
        # WebDriverWait(firefox, 10).until(element_present)
        # 메인페이지에서 목표페이지접근
        time.sleep(3)
        firefox.waite_and_click(
            'mainframe.VFS_MAIN.HFS_MAIN.CF_LEFT.form.btn_8000000:icontext')
        firefox.waite_and_click(
            "mainframe.VFS_MAIN.HFS_MAIN.CF_LEFT.form.pdiv_leftMenu.form.grd_leftMenu.body.gridrow_5.cell_5_0.celltreeitem.treeitemtext:text")
        firefox.waite_and_click(
            "mainframe.VFS_MAIN.HFS_MAIN.CF_LEFT.form.pdiv_leftMenu.form.grd_leftMenu.body.gridrow_8.cell_8_0.celltreeitem.treeitemtext:text")

        notice_title_id = "mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8060300.form.div_work.form.div_search.form.edt_bidNm:input"
        firefox.waite_and_click(notice_title_id)
        firefox.wait_input_text(notice_title_id, notice_title, timeout=3)

        start_date_id = "mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8060300.form.div_work.form.div_search.form.pcl_bidBgngEndDt.form.cal_from.calendaredit:input"
        end_date_id = "mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8060300.form.div_work.form.div_search.form.pcl_bidBgngEndDt.form.cal_to.calendaredit:input"

        firefox.waite_and_click(start_date_id)
        firefox.wait_input_text(start_date_id, f"{start_year}")
        firefox.waite_and_click(end_date_id)
        firefox.wait_input_text(end_date_id, f"{end_year}")

        location_id = "mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8060300.form.div_work.form.div_search.form.div_ctpvSgg.form.cbo_CtpvCd.comboedit:input"
        firefox.waite_and_click(location_id)
        firefox.wait_input_text(location_id, '경남')
        firefox.find_element_by_id(location_id).send_keys(Keys.ENTER)

        time.sleep(2)
        search_button_id = "mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.FS_WORK.win8060300.form.div_work.form.div_search.form.Button00"
        firefox.waite_and_click(search_button_id)
    except Exception as e:
        print(f"Error: {e} Retrying...")
        move_targe_page(firefox, start_year, end_year, notice_title, retries-1)


# %%


def return_process():
    prev_button_css = "#mainframe\\.VFS_MAIN\\.HFS_MAIN\\.VFS_WORK\\.FS_WORK\\.win8060300\\.form\\.div_work\\.form\\.div_page01\\.form\\.div_pagingNo\\.form\\.btn_prev"
    next_button_css = "#mainframe\\.VFS_MAIN\\.HFS_MAIN\\.VFS_WORK\\.FS_WORK\\.win8060300\\.form\\.div_work\\.form\\.div_page01\\.form\\.div_pagingNo\\.form\\.btn_next"
    element = WebDriverWait(driver_instance, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, '#mainframe\\.VFS_MAIN\\.HFS_MAIN\\.VFS_WORK\\.FS_WORK\\.win8060300\\.form\\.div_work\\.form\\.div_page01\\.form\\.div_pagingNo\\.form\\.btn_next'))
    )
    next_button = driver_instance.find_element(
        By.CSS_SELECTOR, next_button_css)
    prev_button = driver_instance.find_element(
        By.CSS_SELECTOR, prev_button_css)
    status_next = next_button.get_attribute('status')
    status_prev = prev_button.get_attribute('status')
    if status_next == 'disabled' or status_prev == 'disabled':
        print(f'disabled next button',)
        return True
    pass


def process_detail_pages(driver_instance, firefox, start_year, end_year, noticetitle):
    current_page = 0
    try_get_detail_element_bool = False
    i = 1
    while True:
        while True:
            if not i < 11:
                break
            try:
                wait = WebDriverWait(driver_instance, 20)
                wait.until(EC.invisibility_of_element_located(
                    (By.ID, 'mainframe.waitwindow')))
                page_button = driver_instance.find_element(
                    By.CSS_SELECTOR, f'#mainframe\\.VFS_MAIN\\.HFS_MAIN\\.VFS_WORK\\.FS_WORK\\.win8060300\\.form\\.div_work\\.form\\.div_page01\\.form\\.div_pagingNo\\.form\\.btn_page{i:02d}')
                page_button.click()
                wait = WebDriverWait(driver_instance, 10)
                elements = wait.until(EC.presence_of_all_elements_located(
                    (By.XPATH, '//div[starts-with(text(), "E") and contains(text(), "-")]')))

                for element in elements:
                    # 상세페이지 진입
                    wait.until(EC.presence_of_all_elements_located(
                        (By.XPATH, '//div[starts-with(text(), "E") and contains(text(), "-")]')))
                    detail = driver_instance.find_elements(
                        By.XPATH, '//div[starts-with(text(), "E") and contains(text(), "-")]')
                    element.click()

                    # 로딩창 대기
                    wait.until(EC.invisibility_of_element_located(
                        (By.ID, 'mainframe.waitwindow')))

                    # 상세페이지 빈화면일 때 새로고침
                    try_get_detail_element_bool = try_get_detail_element()
                    if try_get_detail_element_bool:
                        print('empty page error')
                        driver_instance.refresh()
                        time.sleep(3)
                        move_targe_page(firefox, start_year,
                                        end_year, noticetitle)
                        time.sleep(3)
                        next_button_click(current_page)
                        break

                    # 결과
                    final_result = fetch_and_process_data(driver_instance)
                    insert_data_if_not_exists(final_result)

                    # 상세페이지나가기
                    wait.until(EC.invisibility_of_element_located(
                        (By.ID, 'mainframe.waitwindow')))
                    xbox = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="mainframe.VFS_MAIN.HFS_MAIN.VFS_WORK.CF_MDI.form.div_mdi.form.btn_mdiClosewin8061000"]')))
                    xbox.click()
                i += 1

            except NoSuchElementException as e:
                if return_process():
                    return

            except Exception as e:
                print(e)
                if return_process():
                    return
                driver_instance.refresh()
                time.sleep(3)
                move_targe_page(firefox, start_year, end_year, noticetitle)
                time.sleep(3)
                next_button_click(current_page)

                continue

        if return_process():
            return
        else:
            next_button = driver_instance.find_element(
                By.CSS_SELECTOR, '#mainframe\\.VFS_MAIN\\.HFS_MAIN\\.VFS_WORK\\.FS_WORK\\.win8060300\\.form\\.div_work\\.form\\.div_page01\\.form\\.div_pagingNo\\.form\\.btn_next')
            next_button.click()
            i = 1
            current_page += 1


# %%
def job():
    current_year = datetime.now().year
    current_month = datetime.now().month
    start_end_years = get_month_start_end_dates_with_calendar(current_year, start_month=current_month)
    notice_title_list = ['육류', '축산', '육가금류', '육,가금류']
    for year in start_end_years:
        for noticetitle in notice_title_list:
            print(year, noticetitle)
            time.sleep(2)
            move_targe_page(firefox, year[0], year[1], noticetitle)
            process_detail_pages(driver_instance, firefox, year[0], year[1], noticetitle)
    firefox.quit()
            
import schedule
schedule.every().day.at("09:00").do(job)  # 오전 9시에 실행
schedule.every().day.at("14:00").do(job)  # 오후 2시에 실행
schedule.every().day.at("17:00").do(job)  # 오후 5시에 실행
schedule.every().day.at("19:00").do(job)  # 오후 7시에 실행

if __name__ == '__main__':  
    job()
    while True:
        schedule.run_pending()
        time.sleep(1)