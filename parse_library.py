import json
import os
from argparse import ArgumentParser
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename


def download_txt(url, filename, folder='books/'):
    os.makedirs(folder, exist_ok=True)
    book_filename = f'{sanitize_filename(filename)}.txt'
    book_path = os.path.join(folder, book_filename)
    response = requests.get(url, allow_redirects=False)
    if response.status_code != 200:
        return None

    with open(book_path, 'wb') as download_file:
        download_file.write(response.content)
    return book_path


def download_image(url, filename, folder='images/'):
    os.makedirs(folder, exist_ok=True)
    image_path = os.path.join(folder, filename)
    response = requests.get(url, allow_redirects=False)
    if response.status_code != 200:
        return None

    with open(image_path, 'wb') as download_file:
        download_file.write(response.content)
    return image_path


def get_last_page(url):
    response = requests.get(url=url, allow_redirects=False)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')
    pages = soup.select('p.center a')
    last_page_path = pages[-1]['href']
    last_page = last_page_path.split('/')[-2]
    if last_page.isdigit():
        return int(last_page)
    return None


def get_book_comments(soup):
    return [span.text for span in soup.select('div.texts span.black')]


def get_book_genres(soup):
    return [genre.text for genre in soup.select('span.d_book a')]


def get_book_raw_catalog(url, page_id):
    page_url = f'{url}{page_id}/'
    response = requests.get(page_url, allow_redirects=False)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, 'lxml')
    book_catalog_selector = 'div.bookimage a'
    book_catalog = soup.select(book_catalog_selector)
    return book_catalog


def get_book_properties(url, book_path):
    book_url = urljoin(url, book_path)

    response = requests.get(url=book_url, allow_redirects=False)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')
    title, author = soup.select_one('td.ow_px_td h1').text.split('::')
    title = title.strip()
    author = author.strip()

    text_download_url = urljoin(book_url, f'/txt.php?id={book_path[2:]}')
    book_content_path = download_txt(text_download_url, title)
    if book_content_path is None:
        return None

    book_cover_path = soup.select_one('div.bookimage img')['src']
    book_cover_url = urljoin(book_url, book_cover_path)

    image_filename = book_cover_path.split('/')[-1]
    image_path = download_image(book_cover_url, image_filename)

    return {
        'title': title,
        'author': author,
        'img_src': image_path,
        'book_path': book_content_path,
        'comments': get_book_comments(soup),
        'genres': get_book_genres(soup),
    }


def main():
    parser = ArgumentParser()
    parser.add_argument('--start-page', help='First page number', type=int, default=1)
    parser.add_argument('--end-page', help='Last page number', type=int)
    parser.add_argument('--url', help='Url of section download', default='http://tululu.org/l55/')
    args = parser.parse_args()

    url = args.url

    last_page = get_last_page(url)

    if not args.end_page:
        args.end_page = last_page

    end_page = args.end_page
    start_page = args.start_page

    if end_page > last_page:
        end_page = last_page

    books_descriptions = []
    for page in range(start_page, end_page):

        book_catalog = get_book_raw_catalog(url, page)
        if not book_catalog:
            break
        for book in book_catalog:
            book_path = book['href']
            books_description = get_book_properties(url, book_path)
            if books_description is None:
                print(f'URL {urljoin(url, book_path)} not available. Skipping.')
                continue
            books_descriptions.append(books_description)

    with open('books_description.json', 'w') as file:
        json.dump(obj=books_descriptions, fp=file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
