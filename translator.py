import deepl
import pysrt
import time
import concurrent.futures
from tqdm import tqdm

def translate_subtitle(translator, sub, target_lang="ZH"):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = translator.translate_text(sub.text, target_lang=target_lang)
            return f"{sub.index}\n{sub.start} --> {sub.end}\n{result.text}\n\n"
        except deepl.exceptions.QuotaExceededException:
            raise Exception("DeepL API 配额已用尽。请稍后再试或升级您的计划。")
        except deepl.exceptions.TooManyRequestsException:
            if attempt < max_retries - 1:
                time.sleep(1)  # 等待1秒后重试
                continue
            else:
                raise
        except Exception as e:
            print(f"翻译字幕 {sub.index} 时发生错误: {str(e)}")
            return f"{sub.index}\n{sub.start} --> {sub.end}\n{sub.text} (翻译失败)\n\n"

def translate_srt_file(input_file, output_file, api_key, progress_callback=None):
    translator = deepl.Translator(api_key)

    # 检查 API 密钥是否有效
    try:
        usage = translator.get_usage()
        print(f"DeepL API usage: {usage.character.count}/{usage.character.limit}")
    except deepl.exceptions.AuthorizationException:
        raise Exception("DeepL API 密钥无效。请检查您的 API 密钥。")
    except Exception as e:
        raise Exception(f"检查 DeepL API 密钥时发生错误: {str(e)}")

    subs = pysrt.open(input_file)
    total_subs = len(subs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_sub = {executor.submit(translate_subtitle, translator, sub): sub for sub in subs}

        results = []
        for future in tqdm(concurrent.futures.as_completed(future_to_sub), total=total_subs, desc="Translating"):
            results.append(future.result())
            if progress_callback:
                progress_callback(len(results) / total_subs)

    # 按原始顺序排序结果
    sorted_results = sorted(results, key=lambda x: int(x.split('\n')[0]))

    with open(output_file, 'w', encoding='utf-8') as f:
        for result in sorted_results:
            f.write(result)

    print(f"翻译完成。输出文件: {output_file}")
