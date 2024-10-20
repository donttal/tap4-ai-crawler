from datetime import datetime

def process_translations(data, web_navigation_name, output_file):
    response_data = data['data']
    
    if not web_navigation_name:
        raise ValueError("web_navigation_name cannot be empty")
    
    translations = response_data.get('languages', [])
    
    for translation in translations:
        locale = translation.get('language', '')
        if locale == 'en':
            continue

        title = translation.get('title', '').replace("'", "''")
        content = translation.get('description', '').replace("'", "''")
        detail = translation.get('detail', '').replace("'", "''")
        
        sql_insert = f"""INSERT INTO
public.web_navigation_translations (
web_navigation_name,
locale,
title,
content,
detail
)
VALUES
(
'{web_navigation_name}',
'{locale}',
'{title}',
'{content}',
E'{detail}'
)
ON CONFLICT (web_navigation_id, locale) DO UPDATE
SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    detail = EXCLUDED.detail;
"""
        print("翻译后sql语句生成")
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(sql_insert + "\n")


def process_success_response(data, name, url, description, category_name, monthly_visits, output_file1, output_file2):
    response_data = data['data']

    print("部分调试")
    print(response_data)
    
    # Select the most appropriate tag using Gemini
    tags = response_data.get('tags', [])
    # category_name = select_best_tag(
    #     response_data.get('name', ''),
    #     response_data.get('title', ''),
    #     response_data.get('description', ''),
    #     response_data.get('detail', ''),
    #     tags
    # )
    
    # Prepare the SQL insert statement for the main table
    sql_insert = f"""INSERT INTO
public.web_navigation (
name,
title,
content,
detail,
url,
image_url,
thumbnail_url,
collection_time,
tag_name,
website_data,
star_rating,
category_name,
monthly_visits
)
VALUES
(
'{name}',
'{response_data.get('title', '').replace("'", "''")}',
'{response_data.get('description', '').replace("'", "''")}',
E'{response_data.get('detail', '').replace("'", "''")}',
'{response_data.get('url', '')}',
'{response_data.get('screenshot_data', '')}',
'{response_data.get('screenshot_thumbnail_data', '')}',
'{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}',
NULL,
NULL,
0,
'{category_name}',
'{monthly_visits}'
);
"""
    
    print("原始sql语句生成")
    with open(output_file1, 'a', encoding='utf-8') as f:
        f.write(sql_insert + "\n")
    
    # Process translations
    process_translations(data, name, output_file2)