import csv
import subprocess
import json
from datetime import datetime
from tqdm import tqdm
import os
from dotenv import load_dotenv  # 导入 load_dotenv
import time

from utils import process_success_response

# 加载 .env 文件中的环境变量
load_dotenv()


def run_curl_command(url):
    
    curl_command = [
        'curl', '-X', 'POST',
        '-H', 'Content-Type: application/json',
        '-H', 'Authorization: Bearer 4487f197tap4ai8Zh42Ufi6mAHWGdy',
        '-d', json.dumps({
            "url": url,
            "tags": ["selected tags: ai-detector", "chatbot", "text-writing", "image", "code-it"],
            "languages": ["en", "zh-CN", "zh-TW"]
        }),
        os.getenv('CRAWL_URL') 
    ]
    print("开始执行Crul命令")
    print(str(curl_command))

    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing curl command for URL {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response for URL {url}: {e}")
        return None

def process_csv_and_run_curl(csv_file_path, output_file_path1, output_file_path2):
    failed_rows = []  # 用于存储失败的行
    total_time = 0  # 用于计算总时间
    processed_count = 0  # 处理的行数

    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        name_column_name = 'name'
        url_column_name = 'url'  # Adjust this if your CSV uses a different column name for URLs
        cate_column_name = 'cate' 
        mon_column_name = 'mon' 
        
        for row in tqdm(csv_reader, desc="Processing rows"):  # 使用 tqdm 包装 csv_reader
            name = row.get(name_column_name)
            url = row.get(url_column_name)
            cate = row.get(cate_column_name)
            monthly_visits = row.get(mon_column_name)
            # print("开始爬取"+name)

            if url:
                start_time = time.time()  # 记录开始时间
                print(f"\nProcessing URL: {url}")
                response_data = run_curl_command(url)
                end_time = time.time()  # 记录结束时间
                elapsed_time = end_time - start_time  # 计算耗时
                total_time += elapsed_time  # 累加总时间
                processed_count += 1  # 增加处理计数

                if response_data and response_data.get('code') == 200:
                    process_success_response(response_data, name, url, "", cate, monthly_visits, output_file_path1, output_file_path2)
                    time.sleep(10)
                else:
                    failed_rows.append(row)  # 将失败的行添加到列表中
            else:
                print(f"No URL found in row: {row}")
                failed_rows.append(row)  # 如果没有 URL，也将行添加到失败列表中

    # 计算平均时间
    average_time = total_time / processed_count if processed_count > 0 else 0
    print(f"平均运行时间: {average_time:.2f} 秒")

    # 将失败的行写入新的 CSV 文件
    if failed_rows:
        with open('failed_rows.csv', 'w', newline='') as failed_file:  # 新的 CSV 文件
            fieldnames = ['name', 'url', 'cate', 'mon']  # 根据您的 CSV 列名调整
            writer = csv.DictWriter(failed_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failed_rows)  # 写入失败的行

if __name__ == "__main__":
    print("开始执行")
    csv_file_path = 'input.csv'  # Replace with your CSV file path
    output_file_path1 = 'output/output_sql_statements.sql'  # Replace with your desired output file path
    output_file_path2 = 'output/output_tr_sql_statements.sql'  # Replace with your desired output file path
    process_csv_and_run_curl(csv_file_path, output_file_path1, output_file_path2)