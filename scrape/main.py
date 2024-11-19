import openai
import json
from scrapegraphai.graphs import SmartScraperGraph
import csv

with open('.credentials.json') as f:
    data = json.load(f)

csv_file = 'sponsors.csv'

csv_data = []

graph_config = {
    "llm": {
        "api_key": data['OPENAI_API_KEY'],
        "model": "openai/gpt-4o",
    },
    "verbose": True,
    "headless": False,
}
openai.api_key = data['OPENAI_API_KEY']

with open(csv_file, mode='r') as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        csv_data.append(row)


bullishness_schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "email_choice",
        "schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
            },
            "required": ["url"],
            "additionalProperties": False
        },
        "strict": True
    }
}


for data in csv_data[2:]:
    print(data)

    urls_to_visit = []
    visited_urls = []
    next_url = data['Website']
    attempts = 0

    while True:
        if not next_url.startswith('http'):
            print('Invalid URL')
            break

        attempts += 1
        visited_urls.append(next_url)
        smart_scraper_graph = SmartScraperGraph(
            prompt="Search this page for an email address which would be appropriate for contacting the company about a potential sponsorship opportunity. If the email is not on this page return all URLS which lead to pages owned by the same company which may contain the email address.",
            source=next_url,
            config=graph_config
        )

        result = smart_scraper_graph.run()

        if result['email'] is not None and '@' in result['email']:
            data['email'] = result['email']
            print('located email address: ' + result['email'])
            break
        else:
            for url in result['urls']:
                if url not in urls_to_visit and url not in visited_urls:
                   if not url.startswith('http'):
                       # add the base url to the beginning of the url
                        current_domain_name = next_url.split('/')[2]
                        url = 'http://' + current_domain_name + url
                   urls_to_visit.append(url)
            if attempts > 4:
                print('unable to locate appropriate email address')
                break

        # choose the next url to scrape with openai

        if len(urls_to_visit) > 0:
            url_choose_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are web scraper looking for the url which will lead us to an email address we can use to contact a company about a potential sponsorship opportunity."},
                    {"role": "user", "content": "From the list, choose the best URL to scrape next which will most likely lead to an email we can contact regarding sponsorship: " + ', '.join(urls_to_visit)}
                ],
                temperature=0.0,
                response_format=bullishness_schema,
            )

            video_assessment = json.loads(url_choose_response.choices[0].message.content)
            chosen_url = video_assessment['url']

            next_url = chosen_url

            urls_to_visit.remove(chosen_url)
        else:
            print('No more urls to scrape, could not find an email')
            break


with open('sponsors_with_emails.csv', mode='w') as file:
    fieldnames = csv_data[0].keys()
    writer = csv.DictWriter(file, fieldnames=fieldnames)

    writer.writeheader()
    for row in csv_data:
        writer.writerow(row)