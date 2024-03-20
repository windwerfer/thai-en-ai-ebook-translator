import random
import re
import time

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


def is_the_answer_finished(ai='perplexity'):
    if ai == 'chatGPT':
        # len(driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]'))*2
        #  == len(driver.find_elements(By.CSS_SELECTOR, '.w-full .text-gray-400.visible')) => chatgpt answer complete
        try:
            answers_chatGPT = len(driver.find_elements(By.CSS_SELECTOR, el['chatGPT']['answers_class']))
            answer_edit_icons = len(driver.find_elements(By.CSS_SELECTOR, el['chatGPT']['completed_converstion_parts_marker']))
            if answers_chatGPT * 2 == answer_edit_icons:
                return True
        except Exception as e:
            print('no marker found to check if chatGPT is done answering')
            return False

    if ai == 'perplexity':
        # len(driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]'))*2
        #  == len(driver.find_elements(By.CSS_SELECTOR, '.w-full .text-gray-400.visible')) => chatgpt answer complete
        try:
            stop_button = driver.find_elements(By.CSS_SELECTOR, el['perplexity']['answer_stop_button'])
            return False
        except Exception as e:
            print('no Stop button found -> finished ' + get_hash_identifier())
            return True
    return False


def init_session():
    global driver, actions, attach_to_chrome_remote_debug, el, answer_conent_mem, window_tab_titles

    el = {'chatGPT':{},'perplexity':{},'aiStudio':{}}
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

    el['perplexity']['code_blocks_class'] = ''  # code element
    # el['perplexity']['send_button_class'] = '.grow button svg path[d="M440.6 273.4c4.7-4.5 7.4-10.8 7.4-17.4s-2.7-12.8-7.4-17.4l-176-168c-9.6-9.2-24.8-8.8-33.9 .8s-8.8 24.8 .8 33.9L364.1 232 24 232c-13.3 0-24 10.7-24 24s10.7 24 24 24l340.1 0L231.4 406.6c-9.6 9.2-9.9 24.3-.8 33.9s24.3 9.9 33.9 .8l176-168z"]'  # send button
    # el['perplexity']['send_followup_button_class'] = '.grow button path[d="M209.4 39.4C204.8 34.7 198.6 32 192 32s-12.8 2.7-17.4 7.4l-168 176c-9.2 9.6-8.8 24.8 .8 33.9s24.8 8.8 33.9-.8L168 115.9V456c0 13.3 10.7 24 24 24s24-10.7 24-24V115.9L342.6 248.6c9.2 9.6 24.3 9.9 33.9 .8s9.9-24.3 .8-33.9l-168-176z"]'  # send button
    el['perplexity']['send_button_class'] = '.grow button svg[data-icon="arrow-right"]'  # send button
    el['perplexity']['send_followup_button_class'] = '.grow button svg[data-icon="arrow-up"]'  # send button
    el['perplexity']['answers_class'] = 'div.text-textMain'  # each anser window
    el['perplexity']['question_class'] = 'div[data-message-author-role="user"]'  # each anser window
    el['perplexity']['prompt_textarea'] = 'textarea.col-end-4'
    el['perplexity']['pro_toggle'] = 'button[data-testid="copilot-toggle"]'     # if the botton has the class 'text-textOff' = pro disabled, 'text-super' = pro enabled
    el['perplexity']['send_output_lang_class'] = 'textarea[placeholder="Programming language""]'     # if the botton has the class 'text-textOff' = pro disabled, 'text-super' = pro enabled
    el['perplexity']['answer_stop_button'] = 'svg[data-icon="circle-stop"]'     # if the botton has the class 'text-textOff' = pro disabled, 'text-super' = pro enabled


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

def past_prompt(text, ai='perplexity', click_send=False, speed=0.0001, use_paste=True):
    global driver, el

    prompt, pa = text

    # test for el['perplexity']['answers_class']
    if ai == 'chatGPT':
        wait_for_element_id(el['chatGPT']['prompt_textarea_id'], 30)

    if ai == 'perplexity':
        wait_for_element_class(el['perplexity']['prompt_textarea'], 30)


    # get text input element
    try:
        if ai=='chatGPT':
            promptE = driver.find_element(By.ID, el['chatGPT']['prompt_textarea_id'])

        if ai=='perplexity':
            promptE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['prompt_textarea'])

    except NoSuchElementException as e:
        print('no prompt input field found!')

    # move to prompt field
    actions.move_to_element(promptE).perform()
    promptE.click()

    # enter some question
    # promptE.send_keys(text)
    if use_paste:
        # put text in clipboard
        pyperclip.copy(prompt)

        # past clipboard to element
        promptE.send_keys(Keys.CONTROL + 'v')

        # put text in clipboard
        pyperclip.copy(pa)

        # past clipboard to element
        promptE.send_keys(Keys.CONTROL + 'v')
    else:
        send_text_slowly(promptE, text, speed=speed)

    time.sleep(3)


    # send the prompt
    if click_send:
        # get send prompt button element
        if ai == 'chatGPT':
            try:
                sendE = driver.find_element(By.CSS_SELECTOR, el['chatGPT']['send_button_class'])
            except Exception as e:
                print('no send button found..')
                return
        if ai == 'perplexity':
            wait_untill_no_element_with_innertext("Uploading...")
            # perplexity has 2 butoons
            try:
                sendE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['send_button_class'])
            except Exception as e:
                try:
                    sendE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['send_followup_button_class'])
                except Exception as e:
                    print('no send prompt button found')
                    return

        try:
            actions.move_to_element(sendE).perform()
            sendE.click()
            sendE.click()
        except Exception as e:
            print('couldnt click send on tab ' + get_hash_identifier())

        # perplexity wants to help with the output.. tell it xml
        if ai == 'perplexity':
            time.sleep(1)
            try:
                retLangE = driver.find_element(By.CSS_SELECTOR, el['perplexity']['send_output_lang_class'])
                actions.move_to_element(retLangE).perform()
                send_text_slowly(retLangE, "xml", speed=0.001)
                send_text_slowly(retLangE, "\n", speed=0.01)
                # retLangE.element.send_keys(Keys.ENTER)
            except Exception as e:
                print('couldnt choose the output lang in tab ' + get_hash_identifier())



        return True




def batch_populate(ai='perplexity', nr_of_tabs=1, start_block=0):
    global paragraphs

    window_tab_titles = {}

    paragraphs = unpickle_paragraphs('prj_lp_fug_01')

    groups = my_text.group_paragraphs_by_tokens(paragraphs, max_tokens=3200, prompt_name='to_xml',
                                                process_only_unfinished=False)
    group_id_start = start_block
    groups_to_send_per_tab = 3 # each with 3200 tokens (if thai, english about 900)
    for tab_id in range(nr_of_tabs):
        # new_tab('https://twitter.com/')

        if ai == 'chatGPT':
            new_tab('https://chat.openai.com/')
        if ai=='perplexity':
            new_tab('https://www.perplexity.ai/')


        prompt = """
        You are a translator app now. 

        I give you a part of an xml file with a top-level <items> element that contains multiple <value> elements. 
        Each <value> element has a unique id and some text inside the tag (eg <value id="7">some text</value> ). 
        Output with the same structure into a code block. do not include any explanations.

        Translate the xml elements  into English (you, the awesome translator app). 
        dont translate pali terms like 'dukkha', 'kilesa' or 'samsara', just romanize them.

        """
        pa = ''
        tc = 0
        group_counter = 0
        title = f'{group_id_start}-{group_id_start + groups_to_send_per_tab}'
        tab_id = get_current_tab_id()
        add_hash_identifier(title)
        set_title(title)

        for group_id, paragraph_ids in enumerate(groups):
            # start to add paragraphs when not yet pasted
            if group_id_start > group_id:
                continue
            # if max groups to send to one tab is reached -> dont add any more paragraphs
            if group_counter >= groups_to_send_per_tab:
                continue
            group_counter += 1
            for paragraph_id in paragraph_ids:
                item = paragraphs[paragraph_id]['original']['text']
                item = re.sub(r'\n', ' ', item)
                tc += my_text.token_count(item)
                pa += f'   <item id="{paragraph_id + 2}" bl="{group_id}" tc="{tc}">{item}</item>\n'
        group_id_start = group_id_start + groups_to_send_per_tab

        if ai=='perplexity':
            perplexity_set_focus('Writing')


        past_prompt([prompt, pa], ai=ai, click_send=True, speed=0.0001, use_paste=True)  # speed 0.001 is pretty tame..



    return True

def add_hash_identifier(hash):
    try:

        # JavaScript code to append a hash to the current URL without reloading the page
        script = f"window.location.hash = '{hash}';"

        # Execute the script using Selenium's execute_script method
        driver.execute_script(script)
    except Exception as e:
        print('hash not set')
        return False
    return True

def get_hash_identifier():
    try:
        hash = driver.execute_script("return window.location.hash;")
    except Exception as e:
        print('hash error')
        return ""
    return hash

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
        print('couldnt set Focus to Writing')
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
            #check if chatGPT is still typing
            if not is_the_answer_finished():
                still_running = True
                print(f'still typing "{driver.title}" id_{tab_id}')


            time.sleep(2)

            goto_tab('next')

        if not still_running:
            print('all finished')
            return True

        time.sleep(60)


def cycle_tabs_until_all_finished(ai='perplexity'):

    global window_tab_titles

    for i in range(300):
        # when True, continue to cycle, if False return True (batch comple)
        still_running = False


        tabs_len = len(driver.window_handles)
        for tab in range(tabs_len):

            tab_id = get_current_tab_id()
            #check if tab is finished
            if not is_the_answer_finished(ai):
                still_running = True
                print(f'still typing "{driver.title}" id_{tab_id}')


            time.sleep(2)

            goto_tab('next')

        if not still_running:
            print('all finished')
            return True

        time.sleep(60)


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

    init_session()

    batch_populate(ai='perplexity', nr_of_tabs=5, start_block=1)

    cycle_tabs_until_all_finished()

    # -- session initialized, basic functions defined, all setup and ready to go

    # test_basic_elements()
    # 2x 6 -> quota reached, 1x6 -> works great.. test with 8?
    # batch_populate(ai='chatGPT', nr_of_tabs=9, start_block=54)


    # cycle_tabs_and_start_pompts(click_continue_if_available=True)

    # cycle_tabs_and_continue_output()

    time.sleep(2)

    # # Close the browser
    driver.quit()
