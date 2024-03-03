import requests
import re
import chardet
import html
import os
from bs4 import BeautifulSoup
from uuid import uuid4
from urllib.parse import urljoin


def load_UrlList_from_file(filename):
    """docstring for load_UrlList_from_file"""
    with open(filename, "r") as file:  # Open the file in read mode ('r')
        lines = file.readlines()
    for i in range(0, len(lines)):
        lines[i] = lines[i].rstrip("\n")
    return lines

# encoding needs to match the specified encoding in the html header of the page:
#  eg. <meta http-equiv="Content-Type" content="text/html; charset=windows-874">
#           ->  windows-874 is not supported, use cp874 instead (similar)
#  eg. <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
def download_UrlList_and_save(urlList, folder, encoding='cp874'):
    """Downloads HTML from a URL, saves it with an auto-incremented filename."""
    for i in range(0, len(urlList)):
        url = urlList[i]
        response = requests.get(url)
        response.raise_for_status()  # Raise an error if download fails

        raw_data = response.content

        # Detect the probable encoding
        result = chardet.detect(raw_data)
        probable_encoding = result['encoding']
        print(probable_encoding)
        # text = response.content.decode('utf-8')
        text = response.content.decode(encoding)

        #  no need to convert html to utf8 anymore?
        text = html.unescape(text)

        filename = f"{folder}/{i:03d}_{os.path.basename(url)}"
        with open(filename, "w", encoding='utf-8') as file:
            file.write(text)
            file.write('\nsource:'+url)


def get_filenames(folder_path):
    """Returns a list of all file names within a specified folder."""
    filenames = os.listdir(folder_path)
    return filenames


def get_filenames_by_type(folder_path, extension=".html"):
    """Returns a list of files with a specific extension within a folder."""
    filenames = [file for file in os.listdir(folder_path) if file.endswith(extension)]
    return filenames

def clean_img_tags(html_content):
    """
    Cleans up <img> tags in the provided HTML content.
    It removes all attributes from <img> tags except for the src attribute.

    :param html_content: A string containing HTML content.
    :return: A string with modified HTML content.
    """
    # Regular expression to find <img> tags and capture the src attribute
    regex = r'<img [^>]*src="([^"]*)"[^>]*>'
    
    # Function to replace each <img> tag with a simplified version
    def replace_img_tag(match):
        src = match.group(1)  # Extract the src attribute from the match
        return f'<img src="{src}">'  # Return the simplified <img> tag
    
    # Replace all <img> tags in the HTML content
    cleaned_html = re.sub(regex, replace_img_tag, html_content)
    
    return cleaned_html

def extract_tags(filename, prj_folder, url_webpage, tags=['h','p']):
    """Extracts all <p> tags from an HTML file and returns them as a list."""
    with open(filename, "r") as file:
        contents = file.read()
        soup = BeautifulSoup(contents, "html.parser")
        tags = soup.find_all(tags)
        r = []
        for t in tags:
            # content = t.text
            content = t.decode_contents()

            # remove all html tags that are not img tags
            content = re.sub('<(?!img)[^>]+>',"", content)

            # clean img tags, remove all attibutes that are not src
            # pattern = r"(?<=<img )[^>]+(?=>)|(?<=>)(?!\s*src=)[\s\S]*?(?=<\/img>)"
            # content = re.sub(pattern,'', content)
            content = clean_img_tags(content)
            base_url = "https://www.dharma-gateway.com/monk/monk_biography/lp-chob/"
            content = download_images_and_update_src(content, base_url, prj_folder)
            r.append(content)
        return r

def download_images_and_update_src(text, base_url, prj_folder):
    # Ensure the save directory exists
    save_dir = prj_folder + '/img/'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Regular expression to find <img> tags and their src attributes
    img_tags = re.findall(r'<img [^>]*src="([^"]*)"[^>]*>', text)

    # Process each found img tag
    for src in img_tags:
        # Determine the full URL of the image (handle relative URLs)
        full_url = urljoin(base_url, src)

        try:
            # Generate a unique identifier for the image file
            unique_id = uuid4()
            file_name = f"{unique_id}_{os.path.basename(src)}"
            file_path = os.path.join(save_dir, file_name)

            # Download the image
            response = requests.get(full_url)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)

                # Update the src attribute in the text to the new relative path
                new_src = os.path.join(save_dir, file_name)
                text = text.replace(src, new_src)
            else:
                print(f"Failed to download image from {full_url}")
        except Exception as e:
            print(f"An error occurred when downloading {full_url}: {e}")

    return text


def file_exists(file_path):
    """Checks if a file exists and returns True or False."""
    return os.path.isfile(file_path)

def any_files_exist(folder_path):
    """Checks if any file exists within a folder."""
    for entry in os.listdir(folder_path):
        if os.path.isfile(os.path.join(folder_path, entry)):
            return True  # File found!
    return False  # No files found

def mkdir_if_not_exists(folder):
    try:
        os.makedirs(folder, exist_ok=True)
        print("directory '%s' created successfully" % folder)
    except OSError as error:
        # print("Loading from Project directory '%s' " % folder)
        pass


def prepare_input(prj_folder):

    mkdir_if_not_exists(prj_folder)

    if file_exists(prj_folder + '/input.txt'):
        print('file input/input.txt is present -> will be used as translation source.')
        return 
    
    print('no file input.txt yet. trying to create it from the files in html_source/')

    mkdir_if_not_exists(prj_folder + '/html_source/')

    if any_files_exist(prj_folder + '/html_source/'):
        print('/html_source/ already has downloaded files. download will be skiped and the downloaded files will be used to create input.txt')
    else:
        print(' -- start downloading html pages from the urlList.txt --')
        
        if file_exists(prj_folder + '/urlList.txt')==False:
            print("error: urlList.txt is not present. is needed to create translation source. exit.")
            exit(0)

        urlList = load_UrlList_from_file(prj_folder + '/urlList.txt')

        download_UrlList_and_save(urlList, prj_folder + '/html_source/')


    if any_files_exist(prj_folder + '/html_source/')==False:
        print('error: urlList.txt did not download anything.. no html files to convert to input.txt. exit.')
        exit(0)
    else:
        # get list of files to extract the text from
        files = get_filenames(prj_folder + '/html_source/')
        # if True: breakpoint()
        text = ''
        url_webpage = 'save at the end of the downloaded file: <a href="sorce address"></a>'
        for i in range(0, len(files)):
            t = extract_tags(files[i], prj_folder, url_webpage, tags=['h','p'])
            for i in range(0,len(t)):
                t[i] = re.sub(r'\n',' ', t[i])
                t[i] = t[i].strip()
            tt = "\n\n".join(t)
            text = text + f'\n\n# Chapter {i}\n\n' + tt
        
        # write to input.txt
        if len(text)>0:
            with open(prj_folder + '/input.txt', 'w',encoding="utf-8") as file:  # Open in write mode ('w')
                file.write(text)




if __name__ == "__main__":
    prepare_input('prj_lp_choob_01')
