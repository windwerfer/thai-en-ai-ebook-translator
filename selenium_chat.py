import os
import random
import re
import time

# import win32com.client as comclt
import pyautogui
import pyperclip
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

from compare_translations import unpickle_paragraphs
from lib import my_text
from lib import time_it

def init_session():
    global driver, actions, attach_to_chrome_remote_debug, el, conf, answer_conent_mem, window_tab_titles, prompt

    conf = {}
    conf['project'] = 'prj_lp_fug_01'

    el = {'chatGPT': {}, 'perplexity': {}, 'aiStudio': {}}
    el['chatGPT']['code_blocks_class'] = '.p-4'  # code element
    el['chatGPT']['send_button_class'] = 'button[data-testid="send-button"]'  # send button
    el['chatGPT']['answers_class'] = 'div[data-message-author-role="assistant"]'  # each anser window
    el['chatGPT']['question_class'] = 'div[data-message-author-role="user"]'  # each anser window
    el['chatGPT']['prompt_textarea_id'] = 'prompt-textarea'

    # element changes when screenorientation changes to horizontal, just need to reassign the element with .find_element
    # el['chatGPT']['continue_button_class'] = 'polygon[points="11 19 2 12 11 5 11 19"]'
    el['chatGPT']['continue_button_class'] = '.-rotate-180'

    # len(driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]'))*2
    #  == len(driver.find_elements(By.CSS_SELECTOR, '.w-full .text-gray-400.visible')) => chatgpt answer complete
    el['chatGPT']['completed_converstion_parts_marker'] = '.w-full .text-gray-400.visible'

    el['perplexity']['code_blocks_class'] = 'div.codeWrapper code'  # code element
    el['perplexity']['send_button_class'] = '.grow button svg[data-icon="arrow-right"]'  # send button
    el['perplexity']['send_followup_button_class'] = '.grow button svg[data-icon="arrow-up"]'  # send button
    el['perplexity']['answers_class'] = 'div.text-textMain'  # each anser window
    el['perplexity']['question_class'] = 'div[data-message-author-role="user"]'  # each anser window
    el['perplexity']['prompt_textarea'] = 'textarea.col-end-4'
    # if the botton has the class 'text-textOff' = pro disabled, 'text-super' = pro enabled
    el['perplexity']['pro_toggle'] = 'button[data-testid="copilot-toggle"]'
    el['perplexity']['pro_toggle_inactive'] = 'button.text-textOff[data-testid="copilot-toggle"]'
    el['perplexity']['send_output_lang_class'] = 'textarea[placeholder="Programming language"]'
    el['perplexity']['answer_stop_button'] = 'svg[data-icon="circle-stop"]'
    el['perplexity']['attach_class'] = 'svg[data-icon="circle-plus"]'
    el['perplexity']['skip_followup_button_class'] = 'svg[data-icon="forward"]'

    prompt = {}
    prompt['chatGPT'] = """

    You are a translator app now. 

    I give you a part of an txt file with a xml structure, the top-level element is  <items> and it contains multiple <item> elements. 
    Each <item> element has a unique id and some text inside the tag (eg <item id="7">some text to translate</value> ).
    Output in the same xml structure into a code block. <item> elements can not be merged together for translation or output.
    all items need to be translated in sequence, if max token is reached, simply stop with the warning: max token reached.
    do not include any explanations.

    Translate the txt file into English (you, the awesome translator app). don't put quote characters around pali terms eg.dukkha, sukkha,
    kilesa, deva, khadas, bhāvanā, samādhi, vipassanā, paññā, nirodha, saṅkhāra, dhamma, piṇḍapāta, maha, 
    ārammaṇa, kammaṭṭhāna, vimutti, saññā, vedanā, anicca, rupa, anattā, saṅgha, bhikkhu, vinaya, jhāna, 
    upekkhā, mettā, sammādiṭṭhi, sīla, paññā, saṃsāra, āsavā and write them in romanized pali  
    (like in the example, don't translate them into: suffering, happiness, defilement, angel etc). 

    Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

    passages / quotes in pali need to be romanized and put in quotes (eg. "Evaṃ me sutaṃ"). Take special care to translate places and names correctly.



            """
    prompt['claude'] = """

    You are a translator app now. 

    I give you a part of an txt file with a xml structure, the top-level element is  <items> and it contains multiple <item> elements. 
    Each <item> element has a unique id and some text inside the tag (eg <item id="7">some text to translate</value> ).
    Output in the same xml structure into a code block (surround the xml with ```). <item> elements can not be merged together for translation or output.
    all items need to be translated in sequence, if max token is reached, simply stop with the warning: max token reached.
    do not include any explanations.

    Translate the txt file into English (you, the awesome translator app). put quote characters around pali terms eg.dukkha, sukkha,
    kilesa, deva, khadas, bhāvanā, samādhi, vipassanā, paññā, nirodha, saṅkhāra, dhamma, piṇḍapāta, maha, 
    ārammaṇa, kammaṭṭhāna, vimutti, saññā, vedanā, anicca, rupa, anattā, saṅgha, bhikkhu, vinaya, jhāna, 
    upekkhā, mettā, sammādiṭṭhi, sīla, paññā, saṃsāra, āsavā and write them in romanized pali  
    (like in the example, don't translate them into: suffering, happiness, defilement, angel etc). 

    Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

    passages / quotes in pali need to be romanized and put in quotes (eg. "Evaṃ me sutaṃ"). Take special care to translate places and names correctly.



            """

    continue_prompt = 'continue to translate following the specified rules from above, start 1 item previous before you stoped.'
    continue_prompt = 'translate all <item> from attribute id=0 to id=90, and do not output attribute gr or tk of <item>. '

    window_tab_titles = {}

    user_data_dir = 'C:/Users/watdo/AppData/Local/Google/Chrome/User Data'

    # Setup Chrome options to use the user data directory
    chrome_options = webdriver.ChromeOptions()

    if attach_to_chrome_remote_debug:
        # this one line connect it to chrome remote debugg.. with the debugger account
        # start chrome with debugg mode first:
        #       cd "C:\Program Files\Google\Chrome\Application\"
        #       .\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/ChromeDevSession"
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    else:
        # this will start a new chrome instance, but with the default chrome user account
        chrome_options.add_argument(f'user-data-dir={user_data_dir}')

    # Setup ChromeDriver
    s = Service(ChromeDriverManager().install())

    # Initialize the Chrome driver with the options
    driver = webdriver.Chrome(service=s, options=chrome_options)

    # Apply stealth
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    if attach_to_chrome_remote_debug:
        # Get the title of the current page
        title = driver.title
        print(f'current tab title: {driver.title}')
    else:
        # Open the new webpage
        driver.get('https://chat.openai.com')  # Replace with the URL of the webpage you want to access

    # Create an ActionChains object
    actions = ActionChains(driver)


def click_skip_follow_up_question(ai='perplexity', wait_for_element_loaded=0):
    # # enter follow up input..
    # retLangE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['send_output_lang_class'])
    # actions.move_to_element(retLangE).perform()
    #
    # send_text_slowly(retLangE, "xml", speed=0.001)
    # time.sleep(0.5)
    # send_text_slowly(retLangE, "\n", speed=0.01)

    try:
        # if skip button available, click it
        if wait_for_element_loaded > 0:
            wait_for_element_class(el['perplexity']['skip_followup_button_class'])

        skipE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['skip_followup_button_class'])
        time.sleep(0.2)
        actions.move_to_element(skipE).perform()
        time.sleep(0.2)
        skipE.click()
        time.sleep(0.2)
        return True
    except Exception as e:
        return False


def wait_untill_no_element_with_innertext(text):
    present = True
    i = 0
    while present:
        try:
            elFrom = driver.find_element(By.XPATH, f"//div[text()='{text}']")
        except Exception as e:
            return True
        i += 1
        if i > 120:
            print('waited too long for upload to finish (timeout 120s)')
            return False
        time.sleep(1)
    return True


def wait_for_element_id(element_id, max_seconds_to_wait=10):
    try:
        # Wait up to 10 seconds for the element to be present in the DOM
        element = WebDriverWait(driver, max_seconds_to_wait).until(
            EC.presence_of_element_located((By.ID, element_id))
        )
        print(f"Element with ID '{element_id}' is present.")
    except TimeoutException:
        print(f"Timed out ({max_seconds_to_wait}s) waiting for element with ID '{element_id}' to load.")


def wait_for_element_class(element_class, max_wait=10):
    try:
        # Wait up to 10 seconds for the element to be present in the DOM
        element = WebDriverWait(driver, max_wait).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, element_class))
        )

        print(f"Element with ID '{element_class}' is present.")
    except TimeoutException:
        print(f"Timed out ({max_wait}s) waiting for element with CLASS '{element_class}' to load.")


def get_last_element(element_class):
    elements = driver.find_elements(By.CSS_SELECTOR, element_class)
    # Select the last element from the list
    if elements:  # Check if the list is not empty
        last_element = elements[-1]
        # Now, you can interact with the last_element, e.g., clicking it
        # last_element.click()
    else:
        print(f"No elements with class '{element_class}' found.")
        return False
    return last_element


def wait_untill_element_unchanged(element_class, seconds=5, last_element=True):
    # Specify the locator for the element you want to monitor

    try:
        # Initially wait for the element to be present
        element = get_last_element(element_class)

        unchanged_for = 0
        start_time = time.time()
        previous_text = element.text

        # Loop until the element's text doesn't change for 5 seconds
        while unchanged_for < seconds:
            time.sleep(0.5)  # Check every 0.5 seconds to reduce load
            try:
                # Re-find the element to get the current state
                element = get_last_element(element_class)
                current_text = element.text

                if current_text == previous_text:
                    # Calculate how long the text has been unchanged
                    unchanged_for = time.time() - start_time
                else:
                    # Reset timer if the text has changed
                    previous_text = current_text
                    start_time = time.time()
                    unchanged_for = 0
            except:
                # Handle cases where the element might not be found anymore
                print("Element no longer found.")
                break
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        pass


def send_text_slowly(element, text, speed=0.001):
    for char in text:
        element.send_keys(char)

        pause = random.uniform(speed, speed * 10)  # Generate a random pause between 0.1 and 0.3 seconds
        time.sleep(pause)  # Pause for the generated duration


def get_current_tab_id():
    current_window = driver.current_window_handle
    windows = driver.window_handles
    current_index = windows.index(current_window)
    return current_index


def goto_tab(tab='first'):
    """     the numberings is from newest to oldest (index 0 is the tab created last)

            valid: last, first, next, prev/previous, int (=tab nr), cycle (to see the order)
     """
    global driver

    # valid: cycle, last, first, next, prev/previous or an int
    current_window = driver.current_window_handle

    windows = driver.window_handles
    current_index = windows.index(current_window)
    if tab.isdigit():
        next_index = int(tab)  # Use modulo to loop back to the first tab if at the end
    elif tab == 'first':
        next_index = len(windows) - 1  # Use modulo to loop back to the first tab if at the end
    elif tab == 'last':
        next_index = 0  # Use modulo to loop back to the first tab if at the end
    elif tab == 'next':
        next_index = (current_index - 1) % len(windows)  # Use modulo to loop back to the first tab if at the end
    elif tab == 'prev' or tab == 'previous':
        next_index = (current_index - 1) % len(windows)  # Use modulo to loop back to the first tab if at the end
    elif tab == 'cycle':
        next_index = current_index
        for i in range(20):
            next_index = (next_index + 1) % len(windows)
            driver.switch_to.window(windows[next_index])
            if next_index == 0:
                print('first tab - short pause')
                time.sleep(2)
            time.sleep(1)

    else:
        return False  # Use modulo to loop back to the first tab if at the end

    driver.switch_to.window(windows[next_index])
    return True


def new_tab(url='https://chat.openai.com'):
    global driver
    # https://www.selenium.dev/documentation/webdriver/interactions/windows/
    # driver.execute_script(f"window.open('{url}', '_blank');")
    # goto_tab('last')
    driver.switch_to.new_window('tab')
    # loads a url and waits until loaded
    driver.get(url)
    time.sleep(2)


def is_perplexity_pro_enabled(alert=False):
    try:
        proE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['pro_toggle_inactive'])
        # if element found => pro not enabled
        if alert:
            pyautogui.alert('pro not enabled!!')
        return False
    except Exception as e:
        # pro is enabled
        return True


def is_the_answer_finished(ai='perplexity'):
    if ai == 'chatGPT':
        # len(driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]'))*2
        #  == len(driver.find_elements(By.CSS_SELECTOR, '.w-full .text-gray-400.visible')) => chatgpt answer complete
        try:
            answers_chatGPT = len(driver.find_elements(By.CSS_SELECTOR, el['chatGPT']['answers_class']))
            answer_edit_icons = len(
                driver.find_elements(By.CSS_SELECTOR, el['chatGPT']['completed_converstion_parts_marker']))
            if answers_chatGPT * 2 == answer_edit_icons:
                return True
        except Exception as e:
            print('no marker found to check if chatGPT is done answering')
            return False

    if ai == 'perplexity':
        # len(driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]'))*2
        #  == len(driver.find_elements(By.CSS_SELECTOR, '.w-full .text-gray-400.visible')) => chatgpt answer complete
        try:
            stop_button = driver.find_element(By.CSS_SELECTOR, el['perplexity']['answer_stop_button'])
            return False
        except Exception as e:
            print('no Stop button found -> finished ' + get_identifier())
            return True
    return False


def set_title(title):
    driver.execute_script(f"document.title = '{title}'")


def test_basic_elements():
    global el, driver

    # set title of active window
    driver.execute_script("document.title = 'selenium zombie 1'")

    # get_last_element(element_class)       # last answer
    # driver.find_element(By.CSS_SELECTOR, element_class)
    # driver.find_element(By.ID, element_class)

    wait_for_element_id('prompt-textarea', 30)

    try:
        promptE = driver.find_element(By.ID, el['chatGPT']['prompt_textarea_id'])
    except NoSuchElementException as e:
        print('no prompt input field found!')

    sendE = driver.find_element(By.CSS_SELECTOR, el['chatGPT']['send_button_class'])

    # move to prompt field
    actions.move_to_element(promptE).perform()
    promptE.click()

    # enter some question
    pr = 'hi there'
    promptE.send_keys(pr)

    # send the prompt
    actions.move_to_element(sendE).perform()
    sendE.click()

    # get the last answer element
    answerE = get_last_element(el['chatGPT']['answers_class'])
    answerE.text

    # find the last code element inside the answerE element
    codeE = answerE.find_element(By.XPATH, ".//code[last()]")

    # send some java script
    # driver.execute_script("window.location.href = 'https://chat.openai.com';")
    # driver.execute_script("alert('spookey');")

    # wait untill the last element on the webpage of this class doesnt change any more
    #  eg the AI is done with answering
    wait_untill_element_unchanged(el['chatGPT']['answers_class'], 5, last_element=True)


def click_on_contiune_prompt():
    global el
    try:
        # check if contiune is available
        continueEl = driver.find_element(By.CSS_SELECTOR, el['chatGPT']['continue_button_class'])

        current_window = driver.current_window_handle
        windows = driver.window_handles
        current_index = windows.index(current_window)

        # move to button
        actions.move_to_element(continueEl).perform()
        print(f'continued with window "{driver.title}" id_{current_index}')
        # click
        continueEl.click()
        return True
    except NoSuchElementException as e:
        print('no continue input field found.')
    except Exception as e:
        print('not found, but different error')
    return False


def click_send_prompt(ai='perplexity', wait_for_element_loaded=0):
    """ wait_for_element_loaded = seconds to wait for element to be available before giving up (0=dont wait)"""

    global el

    # get send prompt button element
    if ai == 'chatGPT':

        if wait_for_element_loaded > 0:
            wait_for_element_class(el['chatGPT']['send_button_class'], wait_for_element_loaded)

        try:
            sendE = driver.find_element(By.CSS_SELECTOR, el['chatGPT']['send_button_class'])
        except Exception as e:
            print('no send button found..')
            return False

    if ai == 'perplexity':
        wait_untill_no_element_with_innertext("Uploading...")
        # perplexity has 2 butoons

        if wait_for_element_loaded > 0:
            wait_for_element_class(el['perplexity']['send_button_class'], wait_for_element_loaded)

        try:
            sendE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['send_button_class'])
        except Exception as e:
            try:
                # if it is not the first question of the prompt, the send button is not arrow-left, but arrow-up
                sendE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['send_followup_button_class'])
            except Exception as e:
                print('no send prompt button found')
                return False

    try:
        time.sleep(0.3)
        actions.move_to_element(sendE).perform()
        time.sleep(0.2)
        sendE.click()
        time.sleep(0.3)
    except Exception as e:
        print('couldnt click send on tab ' + get_identifier())


def past_prompt(text, ai='perplexity', click_send=False, speed=0.0001, use_paste=True, project=''):
    global driver, el

    prompt, pa = text

    # test for el['perplexity']['answers_class']
    if ai == 'chatGPT':
        wait_for_element_id(el['chatGPT']['prompt_textarea_id'], 30)

    if ai == 'perplexity':
        wait_for_element_class(el['perplexity']['prompt_textarea'], 30)

    # get text input element
    try:
        if ai == 'chatGPT':
            promptE = driver.find_element(By.ID, el['chatGPT']['prompt_textarea_id'])

        if ai == 'perplexity':
            promptE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['prompt_textarea'])

    except NoSuchElementException as e:
        print('no prompt input field found! ' + get_identifier())

    # move to prompt field
    actions.move_to_element(promptE).perform()
    promptE.click()

    # best option is to use paste to enter the prompt (quick)
    if use_paste:

        time.sleep(0.1)
        # send_text_slowly(promptE, '  ', speed=speed)
        # time.sleep(0.1)

        # put text in clipboard
        pyperclip.copy(prompt)

        # past clipboard to element
        promptE.send_keys(Keys.CONTROL + 'v')

        time.sleep(0.5)

        if ai == 'chatGPT':
            # copy xml to prompt
            pyperclip.copy(pa)
            # past clipboard to element
            promptE.send_keys(Keys.CONTROL + 'v')

        if ai == 'perplexity':

            use_attachent = False
            if use_attachent:  # attach file for text to translate
                # attach file
                attach_file(pa, project, ai='perplexity')

                # wait until upload finished (if attaching file) before continuing
                wait_untill_no_element_with_innertext("Uploading...")
            else:  # simple past for text to translate
                # copy xml to prompt
                pyperclip.copy(pa)
                # past clipboard to element
                promptE.send_keys(Keys.CONTROL + 'v')


    # in case of the "are you human" question
    else:
        send_text_slowly(promptE, prompt + pa, speed=speed)

    time.sleep(3)

    # send the prompt
    if click_send:

        # Scroll to the bottom of the page
        tab_scroll_to_bottom()

        click_send_prompt(ai, wait_for_element_loaded=15)

        time.sleep(2)

        # Scroll to the bottom of the page
        tab_scroll_to_bottom()

        click_send_prompt(ai, wait_for_element_loaded=0)

        # perplexity wants to help with the output.. tell it xml
        if ai == 'perplexity':

            try:
                time.sleep(5)

                # Scroll to the bottom of the page
                tab_scroll_to_bottom()

                time.sleep(2)  # Wait for the page to load after scrolling (adjust as needed)

                # skip follow up input, because it sometimes asks for 2 things..
                click_skip_follow_up_question(ai, wait_for_element_loaded=15)

                time.sleep(2)

                # Scroll to the bottom of the page
                tab_scroll_to_bottom()

                # try a second time, sometimes doesnt work
                click_skip_follow_up_question()

                # retLangE.element.send_keys(Keys.ENTER)
            except Exception as e:
                print('couldnt choose the output lang in tab ' + get_identifier())

        return True


def attach_file(text, project_name, ai='perplexity'):
    # put text in clipboard
    attachE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['attach_class'])
    # attachE.SendKeys("C:\\Some_Folder\\MyFile.txt");
    attachE.click()

    with open(f"{project_name}/paste_tmp.txt", 'w', encoding='utf-8') as file:
        file.write(text)

    abs_script_path = script_directory = os.path.dirname(os.path.abspath(__file__))

    # sleep = 1
    # version 1 (win10):
    # windowsShell = comclt.Dispatch("WScript.Shell")
    # time.sleep(sleep)
    # windowsShell.SendKeys(f'{abs_script_path}\\{project_name}')
    # time.sleep(sleep)
    # windowsShell.SendKeys("{ENTER}")  # can do "{TAB}" as well..
    # time.sleep(sleep)
    # windowsShell.SendKeys(f'paste_tmp.txt')
    # time.sleep(sleep)
    # windowsShell.SendKeys("{ENTER}")  # can do "{TAB}" as well..
    # time.sleep(sleep)

    # version 2 (pip install pyautogui):
    # import pyautogui
    #
    # # Optional: Wait for a few seconds to switch to the window where you want to send the keystrokes
    # time.sleep(5)

    try:
        time.sleep(3)

        # # Find the window with the title 'open'
        # windows = pyautogui.getWindowsWithTitle('Open')
        #
        # if len(windows) > 0:
        #     # If the window is found, activate it to bring it to the foreground
        #     windows[0].activate()
        # else:
        #     print("No window with the title 'open' found.")

        click_on_open_dialog()

        is_window_focused('Open', force=True)

        time.sleep(0.5)

        # go to project path
        pyautogui.typewrite(f'{abs_script_path}\\{project_name}')

        time.sleep(1)

        # Sending the Enter key
        pyautogui.press('enter')

        time.sleep(1)

        # open tmp file (upload)
        pyautogui.typewrite(f'paste_tmp.txt')

        time.sleep(1)

        # Sending the Enter key
        pyautogui.press('enter')

        time.sleep(1)
    except Exception as e:
        print('Attaching file failed')


def click_on_open_dialog():
    try:
        # Find the window with the title 'open'
        windows = pyautogui.getWindowsWithTitle('open')

        if len(windows) > 0:
            # If the window is found, get its coordinates and size
            window = windows[0]
            x, y, width, height = window.left, window.top, window.width, window.height

            # Calculate the center point of the window
            center_x = x + width // 2
            center_y = y + height // 2
            click_y = y + 10

            # Move the mouse to the center of the window
            pyautogui.moveTo(center_x, click_y)

            # Perform a mouse click at the center of the window
            pyautogui.click()
        else:
            print("No window with the title 'open' found.")
    except Exception as e:
        print('window open not found..')


def is_window_focused(window_title, force=False):
    """ if force == True the window must be in the forground, or execution will be blocked"""
    while True:
        try:
            # Get the currently active window
            active_window = pyautogui.getActiveWindow()
            # Check if the active window's title matches the desired window title

            if force:
                if active_window.title == window_title:
                    return True
                else:
                    # if force is set True and the window title does not match the desired one
                    #  display warning and than try again.
                    pyautogui.alert('File choosing dialog not in Focus! \n\n'
                                    'click ok and than click somewere in the file chooser dialog. \n\n'
                                    '(script will continue 5s after the dialog is confirmed)')
                    time.sleep(5)
            else:
                return active_window.title == window_title
        except Exception as e:
            print(f"An error occurred: {e}")
            return False


def batch_populate(ai='perplexity', model='chatGPT', project='prj_lp_fug_01', nr_of_tabs=1, start_block=0,
                   block_range=[], nr_of_groups=1, max_tokens=4000):
    global paragraphs, prompt



    try:
        # if a range is given, open as many tabs as there are elements
        if len(block_range) > 0:
            nr_of_tabs = len(block_range)
    except Exception as e:
        block_range = []

    window_tab_titles = {}

    paragraphs = unpickle_paragraphs(project)

    groups = my_text.group_paragraphs_by_tokens(paragraphs, max_tokens=max_tokens, prompt_name='to_xml',
                                                process_only_unfinished=False)
    group_id_start = start_block
    groups_to_send_per_tab = nr_of_groups  # each with 3200 tokens (if thai, english about 900)
    block_range_done = []

    for tab_id in range(nr_of_tabs):
        # new_tab('https://twitter.com/')

        if ai == 'chatGPT':
            new_tab('https://chat.openai.com/')
        if ai == 'perplexity':
            new_tab('https://www.perplexity.ai/')

        # Switch to the new window, which brings it into focus
        window_handle = driver.current_window_handle
        driver.switch_to.window(window_handle)

        pa = ''
        pa_ids = []
        tc = 0
        group_counter = 0
        tab_id = get_current_tab_id()



        t = {}
        t['group_start'] = ''
        t['group_end'] = ''
        # case: block range give
        if len(block_range) > 0:
            for group_id, paragraph_ids in enumerate(groups):
                # if max groups to send to one tab is reached -> dont add any more paragraphs

                if group_id not in block_range:
                    continue

                # check if the block was already processed
                if group_id in block_range_done:
                    continue

                # if max groups to send to one tab is reached -> dont add any more paragraphs
                if group_counter >= groups_to_send_per_tab:
                    continue

                if group_id in block_range:
                    pa_ids += paragraph_ids
                    group_counter += 1
                    if t['group_start'] == '':
                        t['group_start'] = group_id
                    t['group_end'] = group_id
                    block_range_done.append(group_id)
            title = f'p{pa_ids[0] + 2:0>3}-{pa_ids[-1] + 2:0>3}__g{t['group_start']:0>2}-{t['group_end']:0>2}'


        else:

            # case: no block range is given, but start paragraph
            for group_id, paragraph_ids in enumerate(groups):
                # start to add paragraphs when not yet pasted
                if group_id_start > group_id:
                    continue
                # if max groups to send to one tab is reached -> dont add any more paragraphs
                if group_counter >= groups_to_send_per_tab:
                    continue
                group_counter += 1
                pa_ids +=  paragraph_ids

            title = f'p{groups[group_id_start][0] + 2:0>3}-{groups[group_id_start - 1 + groups_to_send_per_tab][-1] + 2:0>3}__g{group_id_start:0>2}-{group_id_start - 1 + groups_to_send_per_tab:0>2}'

        # set identifier, to keep track of which tab is for what
        set_identifier(title)

        for paragraph_id in pa_ids:
            item = paragraphs[paragraph_id]['original']['text']
            item = re.sub(r'\n', ' ', item)
            tc += my_text.token_count(item)
            # pa += f'   <item id="{paragraph_id + 2}" gr="{group_id}" tk="{tc}">{item}</item>\n'
            pa += f'   <item id="{paragraph_id + 2}">{item}</item>\n'

        group_id_start = group_id_start + groups_to_send_per_tab

        if ai == 'perplexity':
            # check if pro version enabled (otherwise the ai's are only very weak)
            is_perplexity_pro_enabled(alert=True)

            # change from internet search to normal query
            perplexity_set_focus('Writing')

        pr = prompt[model]

        past_prompt([pr, pa], ai=ai, click_send=True, speed=0.0001, use_paste=True,
                    project=project)  # speed 0.001 is pretty tame..

    return True


# to keep track of the tabs through various cases: reload (hash), changes through the pages itself (div)
#  and easily find the corresponding tab (title)
def set_identifier(hash):
    set_identifier_hash(hash)
    set_identifier_div(hash)
    set_title(hash)


# retrieve identifier, whichever is still available
def get_identifier():
    try:
        div = get_identifier_div()

        if div != '':
            set_identifier_hash(div)
            set_title(div)
            return div

        hash = get_identifier_hash()
        hash = hash[1:]  # is returned with '#' as first char
        if hash != '':
            set_identifier_div(hash)
            set_title(hash)
            return hash
    except Exception as e:
        ta = get_current_tab_id()
        print(' problem retrieving or setting identifier in tab ' + str(ta))

    return ''


def set_identifier_hash(hash):
    try:

        # JavaScript code to append a hash to the current URL without reloading the page
        script = f"window.location.hash = '{hash}';"

        # Execute the script using Selenium's execute_script method
        driver.execute_script(script)
    except Exception as e:
        print('hash not set')
        return False
    return True


def get_identifier_hash():
    try:
        hash = driver.execute_script("return window.location.hash;")
    except Exception as e:
        print('get hash error')
        return ""
    return hash


def set_identifier_div(hash):
    if get_identifier_div() == '':
        script = f"""
        var newDiv = document.createElement('div');
        newDiv.id = 'myIdentifierDiv'; // Set an ID for the new div
        newDiv.innerHTML = '{hash}'; // Set content for the new div
        
        // Set style rules
        // newDiv.style.color = 'white'; // Set text color to white
        // newDiv.style.backgroundColor = 'black';
        newDiv.style.cssText = "color: black; background-color: white; position: fixed; z-index: 9999; width: 160px; height: 30px; display: block;";
        
        // add element to very top of page (easier to see, title always gets overridden)
        document.body.insertBefore(newDiv, document.body.firstChild); 
        // document.body.appendChild(newDiv); // Append the new div to the body
        """

        # Execute the script using Selenium's execute_script method
        driver.execute_script(script)


def get_identifier_div():
    try:
        identifierE = driver.find_element(By.ID, 'myIdentifierDiv')
    except NoSuchElementException as e:
        ta = get_current_tab_id()
        print('no identifier div tag found. tab ' + str(ta))
        return ''
    return identifierE.text


def perplexity_set_focus(to='Writing', org='Focus'):
    try:

        # elFrom = driver.find_element(By.XPATH, f"//div[contains(text(), '{org}')]")
        elFrom = driver.find_element(By.XPATH, f"//div[text()='{org}']")
        actions.move_to_element(elFrom).perform()
        elFrom.click()

        time.sleep(1)

        # elTo = driver.find_element(By.XPATH, f"//div[contains(text(), '{to}')]")
        elTo = driver.find_element(By.XPATH, f"//span[text()='{to}']")
        actions.move_to_element(elTo).perform()
        elTo.click()

    except Exception as e:
        print('couldnt set Focus to Writing ' + get_identifier())
        return False

    print('focus set to Writing')
    return True


def cycle_tabs_and_continue_output():
    global window_tab_titles

    for i in range(300):
        # when True, continue to cycle, if False return True (batch comple)
        still_running = False

        tabs_len = len(driver.window_handles)
        for tab in range(tabs_len):

            # if finished typing (try clicking before checking if finished)
            #  return is True -> continue button found & clicked
            if click_on_contiune_prompt():
                still_running = True

            tab_id = get_current_tab_id()
            # check if chatGPT is still typing
            if not is_the_answer_finished():
                still_running = True
                print(f'still typing  id_{tab_id} ' + get_identifier())

            time.sleep(2)

            goto_tab('next')

        if not still_running:
            print('all finished')
            return True

        time.sleep(60)


def cycle_tabs_until_all_finished(ai='perplexity', max_minutes=15):
    global window_tab_titles

    for i in range(max_minutes):
        # when True, continue to cycle, if False return True (batch comple)
        still_running = False

        tabs_len = len(driver.window_handles)
        for tab in range(tabs_len):

            # Scroll to the bottom of the page
            tab_scroll_to_bottom()

            time.sleep(2)  # Wait for the page to load after scrolling (adjust as needed)

            # sometimes it doesnt register the skip follow up click, so doublesave
            click_skip_follow_up_question()

            time.sleep(1)

            tab_id = get_current_tab_id()
            # check if tab is finished
            if not is_the_answer_finished(ai):
                still_running = True
                print(f'still typing id_{tab_id}' + get_identifier())

            time.sleep(2)

            goto_tab('next')

        if not still_running:
            print('all finished')
            return True

        time.sleep(60)


def cycle_tabs_and_close_tabs_starting_with(url_start='https://www.perplexity.ai/'):
    global window_tab_titles

    code_folder = 'code'

    tabs_len = len(driver.window_handles)
    for tab in range(tabs_len):
        code = ''

        try:

            # close tab if code is retrieved
            tab_close_if_url_starts_with(url_start=url_start)

        except Exception as e:
            ta = get_current_tab_id()
            print(f' could not close tab {ta}.')

        time.sleep(1)

        goto_tab('next')


def cycle_tabs_and_collect_code_elements(ai='perplexity', model='chatGPT'):
    global window_tab_titles

    code_folder = 'code'

    tabs_len = len(driver.window_handles)
    for tab in range(tabs_len):
        code = ''

        try:

            tab_scroll_to_bottom()

            codeE = get_last_element(el['perplexity']['code_blocks_class'])
            code = codeE.text + '\n'
            id = get_identifier()

            path = f"{conf['project']}/code_collector_{ai}_{model}/"
            make_dir_if_not_exists(path)
            with open(f"{path}/code_{model}__{id}.xml", 'w', encoding='utf-8') as file:
                file.write(code)


        except Exception as e:
            ta = get_current_tab_id()
            print(f' no code block in tab {ta}.')

        time.sleep(1)

        goto_tab('next')


def make_dir_if_not_exists(directory_path):
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            print(f"Directory '{directory_path}' was created.")
    except Exception as e:
        print(f'couldnt create {directory_path}.')


def cycle_tabs_and_start_pompts(click_continue_if_available=True):
    tabs_len = len(driver.window_handles)
    for tab in range(tabs_len):
        try:

            # check if continue is available
            if click_on_contiune_prompt():
                time.sleep(2)
                continue

            sendE = driver.find_element(By.CSS_SELECTOR, el['chatGPT']['send_button_class'])

            actions.move_to_element(sendE).perform()
            sendE.click()
            print(f'prompt started for  "{driver.title}"')
            time.sleep(2)
        except Exception as e:
            print(f'no send prompt button for  "{driver.title}"')

        time.sleep(2)

        goto_tab('next')


def tab_scroll_to_bottom():
    try:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    except Exception as e:
        print("somehow, couldnt scoll down..")


def tab_close_if_url_starts_with(url_start='https://www.perplexity.ai/'):
    global driver

    # Store the original window handle for later use
    original_window = driver.current_window_handle

    # Get a list of all open tabs' window handles
    open_tabs = driver.window_handles

    for tab in open_tabs:
        # Switch to the tab
        driver.switch_to.window(tab)
        # Check if the tab's URL starts with the specified URL
        if driver.current_url.startswith(url_start):
            # Close the tab
            driver.close()
            # Break the loop if you only want to close the first matching tab
            break

    # Check if the original tab is still open
    if original_window in driver.window_handles:
        # Switch back to the original tab
        driver.switch_to.window(original_window)
    else:
        # If the original tab was closed, switch to the first remaining tab
        driver.switch_to.window(driver.window_handles[0])


if __name__ == '__main__':
    ############# config ###########

    # choose if attaching to already runnig chrome or create new instance
    # start chrome with debugg mode first if set to True:
    #       cd "C:\Program Files\Google\Chrome\Application\"
    #       .\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/ChromeDevSession"
    attach_to_chrome_remote_debug = True

    ############# config end #######

    # TODO: get elements through: div[data-message-author-role="user"] / div[data-message-author-role="assistant"]  -> each new prompt will create a new one, so the last element will be the most recent prompt
    #           data-message-author-role='user'  > code   should display the last code block, and also should show if there is one or if there is an error..

    time_it.timer_start()

    init_session()

    print(' -------- time since program started: ', time_it.elaplsed())

    conf['project_name'] = 'prj_lp_fug_01'
    conf['ai'] = 'perplexity'  # perplexity pro must be enabled to use chatGPT / claude
    conf['model'] = 'claude'  # in perplexity, must be choosen in settings->default ai     claude chatGPT

    # send 3 batch groups, but only process 2?
    # maybe only send max 70 paragraphs??
    # start_block starts with 0
    # nr of groups min 1
    # nr of tabs min 1

    # max token 3300 works well for chatGPT
    # max token 3000 for claude seems too much.. 30% returns
    #  manually is easyer than less tokens i think..
    onlyCollect = False
    onlyCollect = True

    i = 0
    start_block = 51
    nr_of_tabs = 10
    nr_of_cycles = 4
    block_range = []
    # block_range = [48,47]
    while True:

        batch_populate(ai=conf['ai'], model=conf['model'], project=conf['project_name'],
                       nr_of_tabs=nr_of_tabs, block_range=block_range, start_block=nr_of_tabs * i + start_block, nr_of_groups=1, max_tokens=1800)

        cycle_tabs_until_all_finished(max_minutes=5)

        cycle_tabs_and_collect_code_elements(ai=conf['ai'], model=conf['model'])

        i += 1
        # if i > nr_of_cycles:
        #     break

        # if block range has min 1 element -> only one cycle
        try:
            if len(block_range) > 0:
                break
        except Exception as e:
            pass

        cycle_tabs_and_close_tabs_starting_with(url_start='https://www.perplexity.ai/')



        print(f' -------- time since program started (loop {i}): ', time_it.elaplsed())

        time.sleep(6*60)

    # # Close the browser
    driver.quit()
