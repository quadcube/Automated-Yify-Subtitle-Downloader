import os
import re
import urllib
import logging
import requests # pip install requests
from zipfile import ZipFile
from html2text import HTML2Text # pip install html2text

log_path = "/Users/quadcube/Project/Subtitle Tool"
log_name = "file_crawler_w_yts_downloader"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s", handlers=[logging.FileHandler("{0}/{1}.log".format(log_path, log_name)), logging.StreamHandler()])
logger = logging.getLogger()

root_dir = "/Volumes/GoogleDrive/My Drive/Server Backup/WD_MyBookLive_2TB/Public/Shared Videos/" #os.getcwd()
root_url = "http://www.yifysubtitles.com" # 1) www.yifysubtitles.com 2) yts-subs.com (need refinement)
srt_language = ['English']
srt_manual_select = False
refresh_yts_srt = False # if YTS movie files are found, rename any srt files (.backup) in that folder and download the best srt
remove_invalid_srt = True
invalid_srt_size_threshold = 1024 # remove anything less than 1024 bytes if remove_invalid_srt = True
valid_movie_file_ext = ['.mp4', '.m4v', '.avi', '.mkv', '.mov', '.webm', '.flv', '.vob', '.rm', '.rmvb', '.wmv', '.m4v', '.mpeg', '.mpg', '.m2v', '.MTS', '.M2TS', '.TS']

def html2text(url):
    raw_html = requests.get(url)
    raw_html.raise_for_status() # raise exception if status code is not 200
    h = HTML2Text()
    h.ignore_links = False
    return h.handle(raw_html.text) # html2text translate html to readable text
    
def main():
    counter_movie = 0
    counter_movie_w_srt = 0
    counter_movie_dl_srt = 0
    counter_movie_dl_srt_failed = 0
    counter_movie_no_srt = 0
    counter_no_movie = 0
    for dir_name, subdir_list, file_list in os.walk(root_dir): # crawl thru current directory
        if '/' in dir_name[len(root_dir):] or dir_name == root_dir:
            continue    # only transverse one level deep
        else:
            logger.debug('Found dir: {}'.format(dir_name))
            found_srt = False
            counter_movie += 1
            for file_name in file_list:
                if file_name.lower().endswith('.srt'):
                    if refresh_yts_srt == True and ('yts' in file_name.lower() or 'yify' in file_name.lower()):
                        logger.debug('Renaming srt file_list: {}'.format(file_list))
                        os.rename(dir_name + '/' + file_name, dir_name + '/' + file_name[:-4] + '.backup') # rename .srt to .backup
                        break
                    else:
                        logger.debug('Found file_list: {}'.format(file_list))
                        if remove_invalid_srt == True:
                            if os.stat(dir_name + '/' + file_name).st_size < invalid_srt_size_threshold:
                                logger.info('Removing file {}'.format(file_name))
                                os.remove(dir_name + '/' + file_name)
                                break
                                
                        found_srt = True
                        counter_movie_w_srt += 1
                        break
                            
            if found_srt == False:
                try:
                    found_movie = False
                    dir_name_list = dir_name[len(root_dir):].split("(", maxsplit=1)
                    dir_name_year = dir_name_list[1].split(")", maxsplit=1)[0]
                    search_query = dir_name_list[0].strip() # remove year and lead, trailing whitespace as yifisubtitle.com search query will return nothing
                    for i in range(search_query.count(' ') + 1): # i = 0, .replace() does nothing
                        if root_url == "http://www.yifysubtitles.com":
                            text_html = html2text(root_url + '/search?' + urllib.parse.urlencode({'q':search_query.replace(' ', ': ', i).replace(': ', ' ', i-1)})) # Try diff combinations of ":" in the search query
                        else: # yts-subs.com
                            text_html = html2text(root_url + '/search/' + urllib.parse.quote(search_query).replace(' ', ': ', i).replace(': ', ' ', i-1))
                        relevant_results = re.findall('\/movie-imdb\/.+\)\n+.\n+.+\n+.+year', text_html)
                        for result in relevant_results:
                            result_list = result.split(')\n\n[\n\n### ', maxsplit=1)
                            result_link = result_list[0]
                            result_name = result_list[1].split('\n\n')[0]
                            for j in range(5):
                                if result[-5 - j].isdigit(): # as long as not digit, backtrack until digit is found
                                    result_year = result[-8 - j:-4 - j]
                                    break
                            if result_name.lower() == search_query.lower().replace(' ', ': ', i).replace(': ', ' ', i-1) and dir_name_year == result_year:
                                logger.info('Found movie: {} Year: {}'.format(result_name, result_year))
                                found_movie = True
                                break
                        if found_movie == True:
                            break
                    if found_movie == True:
                        text_html = html2text(root_url + result_link)
                        #print(repr(text_html))
                        relevant_results = re.findall('\s\s\n\d{1,}\s?\|\s\s?\w+\s?\|\s\s?\[\s?subtitle\s.+####\sTrailer', text_html, re.DOTALL)
                        if len(relevant_results) > 1:
                            logger.warning('Relevant result more than 1. {}'.format(dir_name))
                        if len(relevant_results) == 0:
                            logger.warning('No srt found on {}! {}'.format(root_url, dir_name))
                        else:
                            relevant_results = relevant_results[0].split('  \n')
                            subtitle_results = {}
                            subtitle_num = 0
                            for result in relevant_results:
                                if result != '':
                                    if result[0].isnumeric():
                                        result = result.replace('\n', '').replace(' ', '').split('|') # first remove the annoying \n, spaces and split according to tags
                                        if result[1] in srt_language:
                                            result_title_link = result[2].replace('[subtitle', '').split('](/subtitles')
                                            subtitle_results[subtitle_num] = {'Rate': int(result[0]), 'Lang': result[1], 'Title': result_title_link[0], 'Link': '/subtitle' + result_title_link[1][:-1] + '.zip', 'Uploader': result[4][1:].split('](')[0] if result[3] == '' else result[3]}
                                            #if srt_manual_select == True:
                                            logger.info('({}) {}'.format(subtitle_num, subtitle_results[subtitle_num]))
                                            subtitle_num += 1
                            if subtitle_num > 0: # check whether there's any filtered srt
                                if srt_manual_select == True and subtitle_num > 0:
                                    while True:
                                        try:
                                            user_selection = int(input('Select subtitle (e.g. 0/1/2/...)'))
                                            if user_selection < len(subtitle_results):
                                                break
                                            else:
                                                raise
                                        except:
                                            print('Option is not valid!')
                                    subtitle_results = subtitle_results[user_selection]
                                else: # Auto srt selection
                                    subtitle_yts_rank = (None, 0) # subtitle_key, rating
                                    subtitle_rank = (None, 0) # subtitle_key, rating
                                    for subtitle_key, subtitle_value in subtitle_results.items():
                                        if subtitle_yts_rank[1] <= subtitle_value['Rate'] and ('yts' in subtitle_value['Title'].lower() or 'yify' in subtitle_value['Title'].lower()): #prioritize YTS tags in title, since most movie files are obtained from YTS'
                                            subtitle_yts_rank = (subtitle_key, subtitle_value['Rate'])
                                        elif subtitle_rank[1] <= subtitle_value['Rate']:
                                            subtitle_rank = (subtitle_key, subtitle_value['Rate'])
                                    if subtitle_yts_rank[0] == None: # if YTS srt is not available, use non-YTS
                                        subtitle_yts_rank = subtitle_rank
                                    subtitle_results = subtitle_results[subtitle_yts_rank[0]]
                                logger.info(subtitle_results)
                                logger.debug(file_list)
                                movie_name = None
                                for file_name in file_list:
                                    for file_type in valid_movie_file_ext:
                                        if file_name.endswith(file_type):
                                            found_movie = file_name.replace(file_type, '.srt')
                                            break
                                if found_movie != None:
                                    with open(dir_name + '/temp_srt.zip', 'wb') as srt_zip_file:
                                        srt_zip_file.write(requests.get(root_url + subtitle_results['Link']).content) # TODO: yts-subs.com subtitles come from www.yifysubtitles.com, hence root_url won't work.
                                    with ZipFile(dir_name + '/temp_srt.zip') as srt_zip_file:
                                        srt_zip_file_list = srt_zip_file.namelist()
                                        for srt_file in srt_zip_file_list:
                                            if srt_file.lower().endswith('.srt'):
                                                srt_zip_file.extract(srt_file, dir_name)
                                                break
                                    os.rename(dir_name + '/' + srt_file, dir_name + '/' + found_movie) # rename srt to match movie file
                                    os.remove(dir_name + '/temp_srt.zip')
                                    counter_movie_dl_srt += 1
                            else:
                                logger.warning('No filtered srt found on {}! {}'.format(root_url, dir_name))
                                counter_movie_no_srt += 1
                    else:
                        logger.warning('No movie found on {}! {}'.format(root_url, dir_name))
                        counter_no_movie += 1
                except Exception as error:
                    logger.exception(error)
                    counter_movie_dl_srt_failed += 1
                    #logger.info(text_html)
                    # Errors caused by line 57 is due to missing year info in dir_name
                    # Errors caused by bad html response code, ignore since there's nothing to do about it
        logger.debug('Current stat -> Movie: {}\tMovie w srt: {}\tMovie dl srt: {}\tMovie dl srt failed: {}\tMovie no srt failed: {}\tNo movie: {}'.format(counter_movie, counter_movie_w_srt, counter_movie_dl_srt, counter_movie_dl_srt_failed, counter_movie_no_srt, counter_no_movie))
    logger.info('Final stat -> Movie: {}\tMovie w srt: {}\tMovie dl srt: {}\tMovie dl srt failed: {}\tMovie no srt failed: {}\tNo movie: {}'.format(counter_movie, counter_movie_w_srt, counter_movie_dl_srt, counter_movie_dl_srt_failed, counter_movie_no_srt, counter_no_movie))
    logging.info('Completed. Exiting...')
if __name__== "__main__":
    main()
