import requests
import openai
import keys
from langs import langs
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from notion.client import NotionClient
from notion.block import CodeBlock
from notion.block import PageBlock
from notion.block import TextBlock
from notion.block import CalloutBlock

openai.api_key = keys.openai
notion_token_v2 = keys.token
notion_page_id = keys.page_id

# create user_agent for data scraping
ua = UserAgent()
user_agent = ua.random
headers = {
    'User-Agent': user_agent
}

def code_comments(param):
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4',
            messages=[
                {'role': 'system', 'content': ''},
                {'role': 'user', 'content': "다음 코드의 작동 원리를 간결하게 한글로 설명해라 (말투는  \"~이다\"): " + param}
            ],
            temperature=0.4
        )
    except:
        print("OpenAI API Error!")
        return
    return response['choices'][0]['message']['content']

def get_problem(prob_n):
    url = "https://solved.ac/api/v3/problem/show"
    querystring = {"problemId": str(prob_n)}
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers, params=querystring)
    except:
        print("Solved.ac API ERROR!")
        return
    data = response.json()
    problemId = data['problemId']
    titleKo = data['titleKo']
    level = data['level']
    tags = [tag['displayNames'][0]['name'] for tag in data['tags']]
    return [problemId, titleKo, level, tags]

def get_code(code_link):
    with requests.Session() as session:

        r = session.get(code_link, headers=headers)
        soup = BeautifulSoup(r.text,'html.parser')

        h1_tag = soup.find('h1', class_="pull-left")
        a_tag = h1_tag.find('a', href=lambda x: x and '/problem/' in x)

        if a_tag:
            href_value = a_tag['href']
            problem_number = href_value.split('/')[-1]

        textarea_tag = soup.find('textarea', {'class': 'form-control no-mathjax codemirror-textarea'})
        if textarea_tag:
            source_code = textarea_tag.text

        divs = soup.find_all('div', {'class': 'col-md-12'})

        for div in divs:
            headline_tag = div.find('div', {'class': 'headline'})
            if headline_tag:
                h2_tag = headline_tag.find('h2')
                if h2_tag:
                    lang = h2_tag.text
                    code_lang = langs[lang]

        return [problem_number, code_lang, source_code]

def post_page(problem_info, submitted_code, code):
    try:
        client = NotionClient(token_v2=notion_token_v2)
    except:
        print("Notion Client Error!")
        return
    page = client.get_block(notion_page_id)

    # page title
    post_title = str(problem_info[0]) + ' - ' + problem_info[1]
    new_page = page.children.add_new(PageBlock, title=post_title)

    # problem link
    link_text_block = new_page.children.add_new(TextBlock)
    link_text_block.title = f'[문제 링크](https://www.acmicpc.net/problem/{problem_info[0]})'

    # page icon
    tier = str(problem_info[2])
    icon_url = f'https://d2gd6pc034wcta.cloudfront.net/tier/{tier}.svg'
    new_page.icon = icon_url

    # page callout
    callout_info = '/'.join(problem_info[3])
    callout = new_page.children.add_new(CalloutBlock)
    callout.title = callout_info
    callout.icon = "💡"
    callout.color = "gray_background"

    # code indent first lines
    code_lines = code.splitlines()
    code_lines = ['\n    ' + line for line in code_lines]
    code = ''.join(code_lines)

    # code block
    new_code_block = new_page.children.add_new(CodeBlock)
    new_code_block.title = code
    new_code_block.language = submitted_code

    # code comments
    new_text_block = new_page.children.add_new(TextBlock)
    new_text_block.title = code_comments("\n".join(code_lines))

    print(f'{problem_info[0]} 커밋 완료')

code_link = input("소스 코드 링크 >> ").strip()

submit_info = get_code(code_link)
problem_info = get_problem(submit_info[0])
post_page(problem_info, submit_info[1], submit_info[2])
