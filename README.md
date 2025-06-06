# 🖼️ Convert-Web

Convert-Web is a simple and powerful web application for converting **images** and **PDF files** into various formats.  
Built with **Python** (Flask) and **HTML**, it offers a clean interface to upload, preview, and download converted files easily.

🚀 **Live Demo:** [https://convert-web.onrender.com](https://convert-web.onrender.com)

> ⚠️ **Notice:** PDF to image conversion is **not supported** on Render.  
> This is because the Render environment **does not include Poppler**, which is required by `pdf2image`.  
> To use PDF conversion, please run the app **locally** or on a server where **Poppler is installed**.

---

## ✨ Features

- 🖼️ Convert between popular image formats (JPG, PNG, WEBP, HEIC, etc.)
- 📄 Convert PDF files to image formats (e.g., PNG, JPG)
- 🔧 Choose image output quality
- 🎯 Select output file type
- ⚡ Fast and lightweight design

---

## 🛠️ Built With

- **Python** – for backend logic and image processing
- **Flask** – as the web framework
- **Pillow** – for image format conversion
- **Poppler** – to convert PDF files to images (`pdf2image` uses Poppler)
- **HTML/CSS** – for the frontend UI
- **Gunicorn** – WSGI server for production deployment
- **Render** – hosting platform for deployment

---

## 📦 Requirements (Local)

Make sure you have **Poppler** installed before running locally.

- 🔗 [Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)
- On macOS:  
  ```bash
  brew install poppler
# Clone this repository
git clone https://github.com/noppakorn001/Convert-Web.git
cd Convert-Web

# Install dependencies
pip install -r requirements.txt

# Run the development server
python app.py

# Or run in production with Gunicorn
gunicorn app:app
