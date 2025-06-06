from flask import Flask, render_template, request, send_file, after_this_request, jsonify
from PIL import Image
import pillow_heif
import os
import uuid
from io import BytesIO
from pdf2image import convert_from_path

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SUPPORTED_FORMATS = [
    ('JPEG', 'JPEG'),
    ('PNG', 'PNG'),
    ('WEBP', 'WEBP'),
    ('HEIC', 'HEIC'),
    ('BMP', 'BMP'),
    ('TIFF', 'TIFF'),
    ('GIF', 'GIF'),
    ('PDF', 'PDF'),
]

def get_lossless_format(ext, multipage=False):
    if multipage:
        return 'TIFF'
    if ext in ['.png', '.bmp', '.tiff', '.tif', '.gif']:
        return ext.replace('.', '').upper()
    return 'PNG'

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        image_file = request.files['image']
        convert_to = request.form['format']
        quality = int(request.form.get('quality', 80))
        original_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
        image_file.save(original_path)
        ext = os.path.splitext(image_file.filename)[1].lower()

        is_lossless = convert_to.lower() == "lossless"
        multipage = False

        # Check if running on Render or in a restricted environment
        is_render = os.environ.get("RENDER", "0") == "1" or os.environ.get("RENDER_EXTERNAL_HOSTNAME") is not None

        if ext == ".pdf" and convert_to.lower() != "pdf":
            if is_render:
                return "PDF conversion is not supported on this hosting platform.", 400
            dpi = int(request.form.get("dpi", 400))
            pdf_fmt = request.form.get("pdf_fmt", convert_to.lower()).lower()
            transparent = request.form.get("transparent") == "on"

            # --- Unzip poppler.zip if not already unzipped and set poppler_path ---
            poppler_zip = os.path.join(os.getcwd(), "poppler.zip")
            poppler_dir = os.path.join(os.getcwd(), "poppler")
            if not os.path.isdir(poppler_dir):
                import zipfile
                if os.path.isfile(poppler_zip):
                    with zipfile.ZipFile(poppler_zip, 'r') as zip_ref:
                        zip_ref.extractall(poppler_dir)
            # Try to find the bin directory inside poppler
            poppler_path = None
            for root, dirs, files in os.walk(poppler_dir):
                if os.path.basename(root).lower() == "bin":
                    poppler_path = root
                    break
            if not poppler_path:
                poppler_path = poppler_dir  # fallback

            try:
                images = convert_from_path(
                    original_path,
                    dpi=dpi,
                    fmt='png' if is_lossless else pdf_fmt,
                    poppler_path=poppler_path,
                    transparent=transparent,
                    thread_count=1,
                    timeout=120
                )
                output_files = []
                for i, img in enumerate(images):
                    if is_lossless:
                        out_ext = 'tiff' if len(images) > 1 else 'png'
                        out_fmt = 'TIFF' if len(images) > 1 else 'PNG'
                        out_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{i+1}.{out_ext}")
                        img.save(out_path, format=out_fmt)
                    else:
                        out_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{i+1}.{convert_to.lower()}")
                        save_kwargs = {}
                        if convert_to.lower() in ['jpeg', 'jpg', 'webp']:
                            save_kwargs['quality'] = quality
                        if convert_to.lower() in ['jpeg', 'jpg', 'webp', 'heic']:
                            img = img.convert("RGB")
                        if convert_to.lower() == 'heic':
                            try:
                                import pillow_heif
                                pillow_heif.register_heif_opener()
                                img.save(out_path, format="HEIC", **save_kwargs)
                            except (KeyError, ImportError):
                                fallback_path = out_path.rsplit('.', 1)[0] + '.jpg'
                                img.save(fallback_path, format="JPEG", **save_kwargs)
                                output_files.append(fallback_path)
                                continue
                        else:
                            img.save(out_path, format=convert_to.upper(), **save_kwargs)
                    output_files.append(out_path)
                del images
                import gc
                gc.collect()
                @after_this_request
                def cleanup(response):
                    try:
                        os.remove(original_path)
                    except Exception:
                        pass
                    for f in output_files:
                        try:
                            os.remove(f)
                        except Exception:
                            pass
                    if len(output_files) > 1:
                        try:
                            os.remove(zipname)
                        except Exception:
                            pass
                    return response
                if len(output_files) == 1:
                    return send_file(output_files[0], as_attachment=True)
                else:
                    import zipfile
                    zipname = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.zip")
                    with zipfile.ZipFile(zipname, 'w') as zf:
                        for f in output_files:
                            zf.write(f, os.path.basename(f))
                    return send_file(zipname, as_attachment=True)
            except Exception as e:
                try:
                    os.remove(original_path)
                except Exception:
                    pass
                return f"Cannot convert PDF to image: {e}", 400

        elif convert_to.lower() == "pdf":
            try:
                im = Image.open(original_path)
                images = []
                try:
                    while True:
                        images.append(im.copy())
                        im.seek(im.tell() + 1)
                except EOFError:
                    pass
                if not images:
                    images = [im]
            except Exception:
                try:
                    os.remove(original_path)
                except Exception:
                    pass
                return "Cannot open image for PDF conversion", 400
            pdf_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.pdf")
            rgb_images = [img.convert("RGB") for img in images]
            rgb_images[0].save(pdf_path, save_all=True, append_images=rgb_images[1:])
            @after_this_request
            def cleanup(response):
                try:
                    os.remove(original_path)
                except Exception:
                    pass
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass
                return response
            return send_file(pdf_path, as_attachment=True)

        elif ext in ['.heic', '.heif']:
            import pillow_heif
            heif_file = pillow_heif.open_heif(original_path)
            im = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw"
            )
        else:
            im = Image.open(original_path)

        try:
            im.seek(1)
            multipage = True
        except Exception:
            multipage = False

        if is_lossless:
            out_fmt = get_lossless_format(ext, multipage)
            out_ext = out_fmt.lower()
            output_name = f"{uuid.uuid4()}.{out_ext}"
            output_path = os.path.join(UPLOAD_FOLDER, output_name)
            if multipage:
                im.seek(0)
                frames = []
                try:
                    while True:
                        frames.append(im.copy())
                        im.seek(im.tell() + 1)
                except EOFError:
                    pass
                if not frames:
                    frames = [im]
                frames[0].save(output_path, save_all=True, append_images=frames[1:], format='TIFF')
            else:
                im.save(output_path, format=out_fmt)
            @after_this_request
            def cleanup(response):
                try:
                    os.remove(original_path)
                except Exception:
                    pass
                try:
                    os.remove(output_path)
                except Exception:
                    pass
                return response
            return send_file(output_path, as_attachment=True)

        else:
            output_name = f"{uuid.uuid4()}.{convert_to.lower()}"
            output_path = os.path.join(UPLOAD_FOLDER, output_name)

            if convert_to.lower() in ['jpeg', 'jpg', 'webp', 'heic']:
                im = im.convert("RGB")

            save_kwargs = {}
            if convert_to.lower() in ['jpeg', 'jpg', 'webp']:
                save_kwargs['quality'] = quality
                if convert_to.lower() == 'webp':
                    save_kwargs['lossless'] = True if quality == 100 else False

            if convert_to.lower() == 'heic':
                try:
                    import pillow_heif
                    pillow_heif.register_heif_opener()
                    im.save(output_path, format="HEIC", **save_kwargs)
                except (KeyError, ImportError):
                    fallback_path = output_path.rsplit('.', 1)[0] + '.jpg'
                    im.save(fallback_path, format="JPEG", **save_kwargs)
                    @after_this_request
                    def cleanup(response):
                        try:
                            os.remove(original_path)
                        except Exception:
                            pass
                        try:
                            os.remove(fallback_path)
                        except Exception:
                            pass
                        return response
                    return send_file(
                        fallback_path,
                        as_attachment=True,
                        download_name=os.path.basename(fallback_path),
                    )
            else:
                im.save(output_path, format=convert_to.upper(), **save_kwargs)

            @after_this_request
            def cleanup(response):
                try:
                    os.remove(original_path)
                except Exception:
                    pass
                try:
                    os.remove(output_path)
                except Exception:
                    pass
                return response

            return send_file(output_path, as_attachment=True)

    return render_template("index.html", supported_formats=SUPPORTED_FORMATS)

@app.route("/cleanup_uploads", methods=["POST"])
def cleanup_uploads():
    try:
        for fname in os.listdir(UPLOAD_FOLDER):
            fpath = os.path.join(UPLOAD_FOLDER, fname)
            try:
                os.remove(fpath)
            except Exception:
                pass
        return jsonify({"status": "ok"})
    except Exception:
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
