import re
import requests

from bs4 import BeautifulSoup
from pcb_utility import *

async def spider_datasheet_info(url: str):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        infos = []
        links = soup.find_all('a', attrs={
            'class': 'no-children',
            'data-navtitle': re.compile(r'(description|pin|layout guidelines)', re.IGNORECASE)
        })
        
        for link in links:
            href = link.get('href', '')
            section_title = link.get('data-navtitle', '')

            full_url = url if not href.startswith('http') else href
            if not href.startswith('http'):
                full_url = f"https:{href}" if href.startswith('/') else f"{url.rstrip('/')}/{href}"

            detail_response = requests.get(full_url, headers=headers, timeout=10)
            detail_response.raise_for_status()
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            content_div = detail_soup.find('div', {'class': 'subsection'})

            if content_div:
                all_subsections = detail_soup.find_all('div', {'class': 'subsection'})
                target_div = None
                
                for subsection in all_subsections:
                    header = subsection.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    
                    if header and section_title.lower() in header.get_text().lower():
                        target_div = subsection
                        break
                
                if target_div:
                    paragraphs_data = []
                    lists_data = []
                    tables_data = []
                    for p in target_div.find_all('p'):
                        text_info = p.get_text(separator=' ', strip=True)
                        text_info = re.sub(r'\s+', ' ', text_info)
                        text_info = text_info.strip()
                        if text_info:
                            paragraphs_data.append(text_info)
                    for li in target_div.find_all('li'):
                        text_info = li.get_text(separator=' ', strip=True)
                        text_info = re.sub(r'\s+', ' ', text_info)
                        text_info = text_info.strip()
                        if text_info:
                            lists_data.append(text_info)
                    for table in content_div.find_all('table'):
                        table_info = await extract_table(table)
                        if table_info:
                            tables_data.append(table_info)
                    info = {
                        'section': section_title,
                        'paragraphs': paragraphs_data,
                        'lists': lists_data,
                        'tables': tables_data
                    }
                    infos.append(info)

        return infos

    except Exception as e:
        print(f"Error reading page: {str(e)}")
        import traceback
        traceback.print_exc()
        return None