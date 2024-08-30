# YouTube Video to PDF Converter

這是一個基於 Streamlit 的網頁應用程序，可以將 YouTube 視頻下載並轉換為 PDF 文件，同時提供字幕翻譯功能。

## 功能

- 下載 YouTube 視頻和字幕
- 將英文字幕翻譯成簡體中文
- 生成包含視頻截圖和字幕的 PDF 文件
- 提供下載選項：MP4 視頻文件、原始 SRT 字幕文件、中文 SRT 字幕文件和生成的 PDF 文件

## 使用方法

1. 安裝依賴：
   ```
   pip install -r requirements.txt
   ```

2. 設置環境變量：
   創建一個 `.env` 文件，並添加您的 DeepL API 密鑰：
   ```
   DEEPL_API_KEY=your_deepl_api_key_here
   ```

3. 運行應用程序：
   ```
   streamlit run app.py
   ```

4. 在瀏覽器中打開顯示的 URL，輸入 YouTube 視頻 URL，然後按照界面提示操作。

## 注意事項

- 確保您有足夠的磁盤空間來存儲下載的視頻和生成的文件。
- 處理長視頻可能需要較長時間，請耐心等待。
- 如果視頻沒有可用的英文字幕，程序將無法處理。

## 依賴項

- streamlit
- python-dotenv
- yt-dlp (用於下載視頻)
- deepl (用於翻譯)
- moviepy (用於視頻處理)
- Pillow (用於圖像處理)
- reportlab (用於生成 PDF)

## 貢獻

歡迎提交 issues 和 pull requests 來改進這個項目。

## 許可證

[MIT License](LICENSE)
