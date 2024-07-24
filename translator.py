import requests
import pysrt
import concurrent.futures
import chardet

def translate_text(text, api_key, target_language='zh'):
    text = text.replace("\h", " ")
    base_url = 'https://api.deepl.com/v2/translate'
    payload = {
        'auth_key': api_key,
        'text': text,
        'target_lang': target_language,
    }
    response = requests.post(base_url, data=payload)
    if response.status_code != 200:
        raise Exception('DeepL request failed with status code {}'.format(response.status_code))
    translated_text = response.json()['translations'][0]['text']
    return translated_text

def translate_srt_file(file_path, api_key, target_language='zh', progress_callback=None):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())

    subs = pysrt.open(file_path, encoding=result['encoding'])

    total_subs = len(subs)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_sub = {executor.submit(translate_text, sub.text, api_key, target_language): sub for sub in subs}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_sub)):
            sub = future_to_sub[future]
            try:
                translated_text = future.result()
                sub.text = translated_text
            except Exception as exc:
                print('%r generated an exception: %s' % (sub, exc))

            if progress_callback:
                progress_callback((i + 1) / total_subs)

    translated_file_path = file_path.replace('.srt', '.zh.srt')
    subs.save(translated_file_path, encoding='utf-8')
    return translated_file_path
