from django.shortcuts import render

# Create your views here.

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import WebDriverException
from minio import Minio
import os
from datetime import datetime
import re

@api_view(['POST'])
def take_screenshot(request):
    url = request.data.get('url')

    width = request.data.get('width', 500)
    height = request.data.get('height', 1080)
    
    if not url:
        return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    uuid_match = re.search(r'([a-f0-9\-]{36})$', url)
    if uuid_match:
        file_uuid = uuid_match.group(1)
    else:
        return Response({'error': 'Invalid URL or UUID not found'}, status=status.HTTP_400_BAD_REQUEST)
    

    print(file_uuid)
    output_file = f'screenshot-{file_uuid}.png'
    
    chrome_options = ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    
    chromedriver_path = '/usr/bin/chromedriver'
    service = ChromeService(executable_path=chromedriver_path)
    
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("document.body.style.overflow = 'hidden';")
        driver.set_window_size(width, height)
        
        driver.get(url)
        driver.save_screenshot(output_file)
        
        # Upload to MinIO
        minio_client = Minio(
            os.getenv('MINIO_ENDPOINT', 'minio:9000'),
            access_key=os.getenv('MINIO_ACCESS_KEY'),
            secret_key=os.getenv('MINIO_SECRET_KEY'),
            secure=False
        )
        
        bucket_name = os.getenv('MINIO_BUCKET_THUMBNAIL', 'thumbnail')
        
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
        
        file_name = os.path.basename(output_file)

        print(file_name)

        file_path_in_bucket = get_file_path(file_uuid, bucket_name)
        
        minio_client.fput_object(
            bucket_name,
            file_path_in_bucket,
            output_file,
            content_type='image/png'
        )

        path = f"{bucket_name}/{file_path_in_bucket}"
        
        cdn_link = f'http://localhost:9000/{path}'

        data = {
            'data': {
                'link': cdn_link
            }
        }
        return Response(data, status=status.HTTP_200_OK)
        
    except WebDriverException as e:
        return Response({'error': f'WebDriverException: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        if 'driver' in locals():
            driver.quit()
        
        if os.path.exists(output_file):
            os.remove(output_file)

# def get_file_path(file_name):
#     today = datetime.now().strftime('%Y-%m-%d')
#     return f'templates/{today}/{file_name}'

def get_file_path(file_uuid, bucket_name):
    today = datetime.now().strftime('%Y-%m-%d')
    return f'templates/{today}/{file_uuid}.jpg'

@api_view(['GET'])
def home(request):
    data = {
        'code': "success",
        'message': "It's working"
    }
    return Response(data)