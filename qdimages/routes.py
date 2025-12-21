"""
Image management routes for qdimages.

Provides all Flask routes for image upload, storage, editing, browsing, and serving.
"""

import os
import sys
import uuid
import yaml
from datetime import datetime
from flask import request, jsonify, session, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image

# Import from qdimages package
from qdimages import image_bp
from qdimages.editor import ImageEditor
from qdimages.file_handler import ImageFileHandler
from qdimages.storage import ImageStorage

# These will be initialized when the blueprint is registered
image_handler = None
image_storage = None


def init_handlers(app):
    """Initialize image handler and storage instances."""
    global image_handler, image_storage

    # Legacy flat storage handler (for backwards compatibility)
    image_handler = ImageFileHandler(
        default_directory=app.config.get('UPLOAD_FOLDER', './uploads')
    )

    # Hierarchical storage handler
    image_storage = ImageStorage(
        base_path=app.config['IMAGES_BASE_PATH'],
        db_path=os.path.join(os.path.dirname(app.instance_path), 'commercenode.db')
    )


def get_session_id():
    """Get or create a session ID for temporary files"""
    if 'iedit_session_id' not in session:
        session['iedit_session_id'] = str(uuid.uuid4())
    return session['iedit_session_id']


def get_temp_filename(original_path, seq=1):
    """Generate temporary filename: iedit.<session_id>.<seq>.<ext>"""
    from pathlib import Path
    ext = Path(original_path).suffix
    session_id = get_session_id()
    return os.path.join(current_app.config['TEMP_DIRECTORY'], f'iedit.{session_id}.{seq}{ext}')


@image_bp.before_app_request
def setup_handlers():
    """Initialize handlers before first request."""
    global image_handler, image_storage
    if image_handler is None or image_storage is None:
        init_handlers(current_app)


# ==================== Image Serving ====================

@image_bp.route("/images/<path:filename>")
@login_required
def serve_image(filename):
    """Serve images from hierarchical storage, test_images, uploads, or temp directory"""
    # Decode URL-encoded path
    from urllib.parse import unquote
    filename = unquote(filename)

    # Check for hierarchical storage path pattern: dir1/dir2/sequence.ext
    # Pattern: 2-char hex / 2-char hex / number.ext
    import re
    hierarchical_pattern = r'^[0-9a-f]{2}/[0-9a-f]{2}/\d+\.\w+$'
    if re.match(hierarchical_pattern, filename, re.IGNORECASE):
        # This is a hierarchical storage path
        hierarchical_path = os.path.join(current_app.config['IMAGES_BASE_PATH'], filename)
        if os.path.exists(hierarchical_path) and os.path.isfile(hierarchical_path):
            directory = os.path.dirname(hierarchical_path)
            basename = os.path.basename(hierarchical_path)
            return send_from_directory(directory, basename)

    # Flask's <path:> strips leading slash, add it back for absolute paths
    if not filename.startswith('/') and not filename.startswith('\\'):
        filename = '/' + filename

    # Check if file exists and is in allowed directory
    if os.path.exists(filename) and os.path.isfile(filename):
        # Check upload folder
        if image_handler.validate_path(filename, current_app.config['UPLOAD_FOLDER']):
            directory = os.path.dirname(filename)
            basename = os.path.basename(filename)
            return send_from_directory(directory, basename)

        # Check temp directory
        if image_handler.validate_path(filename, current_app.config['TEMP_DIRECTORY']):
            directory = os.path.dirname(filename)
            basename = os.path.basename(filename)
            return send_from_directory(directory, basename)

    # Try uploads directory (check basename only)
    uploads_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(filename))
    if os.path.exists(uploads_path):
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], os.path.basename(filename))

    current_app.logger.error(f"Image not found or invalid path: {filename}")
    return "Image not found", 404


# ==================== Metadata ====================

@image_bp.route("/api/images/metadata", methods=["POST"])
@login_required
def load_metadata():
    """API: Load YAML metadata for an image if it exists"""
    try:
        data = request.get_json()
        filepath = data.get('filepath')

        if not filepath:
            return jsonify({'success': False, 'error': 'No filepath provided'}), 400

        # Check for corresponding YAML file
        yaml_path = os.path.splitext(filepath)[0] + '.yaml'

        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r') as f:
                    metadata = yaml.safe_load(f)

                # Store in session for future use
                session['iedit_loaded_metadata'] = metadata

                current_app.logger.info(f"Loaded metadata from {yaml_path}")
                return jsonify({
                    'success': True,
                    'metadata': metadata,
                    'has_metadata': True
                })
            except Exception as e:
                current_app.logger.error(f"Error reading YAML metadata: {str(e)}")
                return jsonify({'success': False, 'error': f'Failed to read metadata: {str(e)}'}), 500
        else:
            # No metadata file exists
            return jsonify({
                'success': True,
                'has_metadata': False
            })

    except Exception as e:
        current_app.logger.error(f"Error loading metadata: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@image_bp.route("/api/images/metadata/update", methods=["POST"])
@login_required
def update_metadata():
    """API: Update image metadata (keywords)"""
    try:
        data = request.get_json()
        image_id = data.get('image_id')
        keywords = data.get('keywords', '')

        if not image_id:
            return jsonify({'success': False, 'error': 'image_id required'}), 400

        # Update database
        import sqlite3
        conn = sqlite3.connect(str(image_storage.db_path))
        cursor = conn.cursor()

        # First verify image exists
        cursor.execute("SELECT dir1, dir2, filename FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Image not found'}), 404

        dir1, dir2, filename = row

        # Update keywords in database
        cursor.execute("UPDATE images SET keywords = ? WHERE id = ?", (keywords, image_id))
        conn.commit()
        conn.close()

        # Update YAML file
        yaml_path = os.path.join(current_app.config['IMAGES_BASE_PATH'], dir1, dir2,
                                 os.path.splitext(filename)[0] + '.yaml')

        try:
            image_storage.save_yaml_metadata(image_id, yaml_path)
            current_app.logger.info(f"Updated metadata for image {image_id}")
        except Exception as e:
            current_app.logger.error(f"Failed to update YAML file: {str(e)}")
            # Don't fail the request if YAML update fails, database is source of truth

        return jsonify({
            'success': True,
            'message': 'Metadata updated successfully',
            'image_id': image_id,
            'keywords': keywords
        })

    except Exception as e:
        current_app.logger.error(f"Error updating metadata: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# File continues in next message due to length...

# ==================== Image Processing ====================

@image_bp.route("/api/images/process", methods=["POST"])
@login_required
def process_image():
    """
    API: Process image with requested operations
    Expects JSON: {
        "filepath": "/path/to/image.jpg",
        "operations": [
            {"type": "crop", "coords": [x1, y1, x2, y2]},
            {"type": "brilliance", "brightness": 1.2, "contrast": 1.1},
            {"type": "remove_background"},
            {"type": "resize", "width": 800, "height": 600}
        ]
    }
    Returns: {"success": true, "output_path": "..."}
    """
    try:
        data = request.get_json()
        filepath = data.get('filepath')
        operations = data.get('operations', [])

        if not filepath:
            return jsonify({'success': False, 'error': 'No filepath provided'}), 400

        # Security: validate path
        valid_path = False
        full_filepath = filepath  # Will be set to absolute path if needed

        # Check for hierarchical storage path pattern: dir1/dir2/sequence.ext
        import re
        hierarchical_pattern = r'^[0-9a-f]{2}/[0-9a-f]{2}/\d+\.\w+$'
        if re.match(hierarchical_pattern, filepath, re.IGNORECASE):
            # This is a hierarchical storage path
            full_filepath = os.path.join(current_app.config['IMAGES_BASE_PATH'], filepath)
            if os.path.exists(full_filepath) and os.path.isfile(full_filepath):
                valid_path = True
        # Check if it's in upload folder
        elif image_handler.validate_path(filepath, current_app.config['UPLOAD_FOLDER']):
            valid_path = True
            full_filepath = filepath
        # Check if it's in temp directory
        elif image_handler.validate_path(filepath, current_app.config['TEMP_DIRECTORY']):
            valid_path = True
            full_filepath = filepath

        if not valid_path:
            return jsonify({'success': False, 'error': 'Invalid file path'}), 403

        # Initialize metadata if processing original file (not a temp file)
        if 'iedit_metadata' not in session or not full_filepath.startswith(current_app.config['TEMP_DIRECTORY']):
            session['iedit_metadata'] = {
                'file_id': os.path.basename(filepath),
                'brightness': 1.0,
                'contrast': 1.0
            }

        # Load image
        image = image_handler.load_image(full_filepath)

        # Auto-orient based on EXIF
        image = ImageEditor.auto_orient(image)

        # Apply operations in sequence and track metadata
        for op in operations:
            op_type = op.get('type')

            if op_type == 'crop':
                coords = op.get('coords')
                if coords and len(coords) == 4:
                    # Only save first crop coordinates (relative to original source)
                    if 'crop' not in session['iedit_metadata']:
                        session['iedit_metadata']['crop'] = {
                            'upper_left_x': coords[0],
                            'upper_left_y': coords[1],
                            'lower_right_x': coords[2],
                            'lower_right_y': coords[3]
                        }
                    image = ImageEditor.crop_image(image, coords)

            elif op_type == 'brilliance':
                brightness = op.get('brightness', 1.0)
                contrast = op.get('contrast', 1.0)
                # Track cumulative brightness/contrast (they multiply)
                session['iedit_metadata']['brightness'] *= brightness
                session['iedit_metadata']['contrast'] *= contrast
                image = ImageEditor.adjust_brilliance(image, brightness, contrast)

            elif op_type == 'remove_background':
                session['iedit_metadata']['background_removed'] = True
                image = ImageEditor.remove_background(image)

            elif op_type == 'resize':
                width = op.get('width')
                height = op.get('height')
                if width or height:
                    image = ImageEditor.resize(image, width=width, height=height)

        # Save to temporary file
        temp_path = get_temp_filename(full_filepath, seq=1)
        output_path = image_handler.save_image(image, temp_path, suffix="")

        # Update final image dimensions in metadata
        session['iedit_metadata']['width'] = image.width
        session['iedit_metadata']['height'] = image.height

        # Store original filepath in session for later save (only if not already a temp file)
        # This prevents overwriting the original source path when processing temp files multiple times
        if not full_filepath.startswith(current_app.config['TEMP_DIRECTORY']):
            session['iedit_original_path'] = filepath  # Store relative path for hierarchical images

        return jsonify({
            'success': True,
            'output_path': output_path,
            'filename': os.path.basename(output_path),
            'is_temp': True
        })

    except Exception as e:
        current_app.logger.error(f"Error processing image: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Upload & Save ====================

@image_bp.route("/api/images/upload", methods=["POST"])
@login_required
def upload_image():
    """API: Handle file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Validate file extension
        ext = os.path.splitext(file.filename)[1].lower()
        allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'.jpg', '.jpeg', '.png', '.gif'})
        if ext not in [f".{e}" if not e.startswith('.') else e for e in allowed]:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

        # Secure the filename
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        # Save file
        file.save(filepath)

        return jsonify({
            'success': True,
            'filepath': filepath,
            'filename': filename
        })

    except Exception as e:
        current_app.logger.error(f"Error uploading image: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@image_bp.route("/api/images/save", methods=["POST"])
@login_required
def save_final_image():
    """API: Save image to hierarchical storage with hash-based content addressing"""
    try:
        # Get the temp file path and keywords from request
        data = request.get_json()
        temp_path = data.get('temp_path')
        keywords = data.get('keywords', '')

        if not temp_path or not os.path.exists(temp_path):
            return jsonify({'success': False, 'error': 'Temporary file not found'}), 404

        # Load image with PIL
        image = Image.open(temp_path)

        # Get metadata from session to build transformations
        metadata = session.get('iedit_metadata', {})
        transformations = {}

        # Get original file info for source tracking
        original_path = session.get('iedit_original_path')
        if original_path:
            transformations['file_id'] = os.path.basename(original_path)

        # Add crop if it exists
        if 'crop' in metadata:
            transformations['crop'] = metadata['crop']

        # Add brightness if changed
        brightness = metadata.get('brightness', 1.0)
        if brightness != 1.0:
            transformations['brightness'] = round(brightness, 3)

        # Add contrast if changed
        contrast = metadata.get('contrast', 1.0)
        if contrast != 1.0:
            transformations['contrast'] = round(contrast, 3)

        # Add background_removed flag if set
        if metadata.get('background_removed'):
            transformations['background_removed'] = True

        # Determine source_image_id if this is an edited image
        source_image_id = None

        # Save to hierarchical storage
        result = image_storage.save_image_with_metadata(
            image=image,
            keywords=keywords,
            source_image_id=source_image_id,
            transformations=transformations if transformations else None,
            user_id=current_user.id if current_user and current_user.is_authenticated else None
        )

        if not result['success']:
            # Check if it's a duplicate
            if result.get('duplicate'):
                return jsonify({
                    'success': False,
                    'error': result['error'],
                    'duplicate': True,
                    'existing_path': result.get('existing_path')
                }), 409  # Conflict
            else:
                return jsonify({'success': False, 'error': result['error']}), 500

        # Clean up temp file
        try:
            os.remove(temp_path)
        except Exception as e:
            current_app.logger.warning(f"Failed to remove temp file {temp_path}: {str(e)}")

        # Clear metadata from session
        session.pop('iedit_metadata', None)
        session.pop('iedit_original_path', None)

        return jsonify({
            'success': True,
            'image_id': result['image_id'],
            'path': result['path'],
            'full_path': result['full_path'],
            'xxhash': result['xxhash']
        })

    except Exception as e:
        current_app.logger.error(f"Error saving image to hierarchical storage: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Browse & Search ====================

@image_bp.route("/api/images/list", methods=["GET"])
@login_required
def list_images():
    """API: List images in directory (AJAX) - Legacy support"""
    try:
        directory = request.args.get('directory', current_app.config['UPLOAD_FOLDER'])
        images = image_handler.list_images(directory)
        return jsonify({'success': True, 'files': images})
    except Exception as e:
        current_app.logger.error(f"Error listing images: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@image_bp.route("/api/images/browse", methods=["GET"])
@login_required
def browse_hierarchical():
    """API: Browse hierarchical image directory structure"""
    try:
        dir1 = request.args.get('dir1')
        dir2 = request.args.get('dir2')

        images_base = current_app.config['IMAGES_BASE_PATH']

        # If no parameters, list top-level directories (dir1)
        if not dir1:
            path = images_base
            if not os.path.exists(path):
                return jsonify({'success': True, 'type': 'directories', 'items': []})

            # List all dir1 directories
            dirs = []
            for name in os.listdir(path):
                dir_path = os.path.join(path, name)
                if os.path.isdir(dir_path) and len(name) == 2:
                    # Count subdirectories (dir2)
                    subdir_count = sum(1 for x in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, x)))
                    dirs.append({
                        'name': name,
                        'type': 'dir1',
                        'subdir_count': subdir_count
                    })

            dirs.sort(key=lambda x: x['name'])
            return jsonify({'success': True, 'type': 'directories', 'level': 'dir1', 'items': dirs})

        # If dir1 but no dir2, list dir2 directories
        elif dir1 and not dir2:
            path = os.path.join(images_base, dir1)
            if not os.path.exists(path):
                return jsonify({'success': True, 'type': 'directories', 'items': []})

            dirs = []
            for name in os.listdir(path):
                dir_path = os.path.join(path, name)
                if os.path.isdir(dir_path) and len(name) == 2:
                    # Count image files
                    image_count = sum(1 for x in os.listdir(dir_path) if x.endswith(('.jpg', '.jpeg', '.png', '.gif')))
                    dirs.append({
                        'name': name,
                        'type': 'dir2',
                        'image_count': image_count
                    })

            dirs.sort(key=lambda x: x['name'])
            return jsonify({'success': True, 'type': 'directories', 'level': 'dir2', 'parent': dir1, 'items': dirs})

        # If both dir1 and dir2, list images
        else:
            path = os.path.join(images_base, dir1, dir2)
            if not os.path.exists(path):
                return jsonify({'success': True, 'type': 'images', 'items': []})

            images = []
            for filename in os.listdir(path):
                filepath = os.path.join(path, filename)

                # Only include image files
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                    continue

                if not os.path.isfile(filepath):
                    continue

                # Get file stats
                stat = os.stat(filepath)

                images.append({
                    'filename': filename,
                    'path': f"{dir1}/{dir2}/{filename}",
                    'size': f"{stat.st_size / 1024:.1f} KB",
                    'size_bytes': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })

            # Sort by filename (which is sequential)
            images.sort(key=lambda x: int(os.path.splitext(x['filename'])[0]))

            return jsonify({
                'success': True,
                'type': 'images',
                'parent': f"{dir1}/{dir2}",
                'items': images
            })

    except Exception as e:
        current_app.logger.error(f"Error browsing hierarchical storage: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@image_bp.route("/api/images/search", methods=["POST"])
@login_required
def search_images():
    """API: Search images by metadata (keywords, date, dimensions, format)"""
    try:
        data = request.get_json()
        keywords = data.get('keywords', '').strip()
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        format_filter = data.get('format')
        width_min = data.get('width_min')
        height_min = data.get('height_min')
        limit = data.get('limit', 100)

        # Build SQL query
        query = "SELECT id, xxhash, dir1, dir2, filename, format, width, height, file_size, keywords, created_at FROM images WHERE 1=1"
        params = []

        # Keyword search (simple LIKE for now, could upgrade to FTS5)
        if keywords:
            # Split keywords and search for each
            keyword_terms = keywords.split()
            keyword_conditions = []
            for term in keyword_terms:
                keyword_conditions.append("keywords LIKE ?")
                params.append(f"%{term}%")

            if keyword_conditions:
                query += " AND (" + " OR ".join(keyword_conditions) + ")"

        # Date range filter
        if date_from:
            query += " AND created_at >= ?"
            params.append(date_from)

        if date_to:
            query += " AND created_at <= ?"
            params.append(date_to)

        # Format filter
        if format_filter:
            query += " AND format = ?"
            params.append(format_filter.upper())

        # Dimension filters
        if width_min:
            query += " AND width >= ?"
            params.append(int(width_min))

        if height_min:
            query += " AND height >= ?"
            params.append(int(height_min))

        # Order by most recent first
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        # Execute query
        import sqlite3
        conn = sqlite3.connect(str(image_storage.db_path))
        cursor = conn.cursor()

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                'image_id': row[0],
                'xxhash': row[1],
                'path': f"{row[2]}/{row[3]}/{row[4]}",
                'filename': row[4],
                'format': row[5],
                'width': row[6],
                'height': row[7],
                'size': f"{row[8] / 1024:.1f} KB",
                'keywords': row[9] or '',
                'created_at': row[10]
            })

        conn.close()

        return jsonify({
            'success': True,
            'count': len(results),
            'results': results
        })

    except Exception as e:
        current_app.logger.error(f"Error searching images: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Temp Staging ====================

@image_bp.route("/api/images/temp-staging/list", methods=["GET"])
@login_required
def list_temp_staging():
    """API: List files in temp_images staging area"""
    try:
        temp_images_path = current_app.config['TEMP_IMAGES_PATH']

        if not os.path.exists(temp_images_path):
            return jsonify({'success': True, 'files': []})

        files = []
        for filename in os.listdir(temp_images_path):
            filepath = os.path.join(temp_images_path, filename)

            # Only include actual files (not directories)
            if not os.path.isfile(filepath):
                continue

            # Check if it's an image file
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                continue

            # Get file stats
            stat = os.stat(filepath)

            files.append({
                'name': filename,
                'path': filepath,
                'size': f"{stat.st_size / 1024:.1f} KB",
                'size_bytes': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)

        return jsonify({'success': True, 'files': files})

    except Exception as e:
        current_app.logger.error(f"Error listing temp staging files: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@image_bp.route("/api/images/temp-staging/import", methods=["POST"])
@login_required
def import_from_staging():
    """API: Import image from temp_images staging area to hierarchical storage"""
    try:
        data = request.get_json()
        filepath = data.get('filepath')
        keywords = data.get('keywords', '')

        if not filepath or not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404

        # Validate file is in temp_images directory
        temp_images_path = os.path.abspath(current_app.config['TEMP_IMAGES_PATH'])
        filepath_abs = os.path.abspath(filepath)

        if not filepath_abs.startswith(temp_images_path):
            return jsonify({'success': False, 'error': 'Invalid file path'}), 403

        # Load image with PIL
        image = Image.open(filepath)

        # Save to hierarchical storage
        result = image_storage.save_image_with_metadata(
            image=image,
            keywords=keywords,
            source_image_id=None,
            transformations=None,
            user_id=current_user.id if current_user and current_user.is_authenticated else None
        )

        if not result['success']:
            # Check if it's a duplicate
            if result.get('duplicate'):
                return jsonify({
                    'success': False,
                    'error': result['error'],
                    'duplicate': True,
                    'existing_path': result.get('existing_path')
                }), 409  # Conflict
            else:
                return jsonify({'success': False, 'error': result['error']}), 500

        # Delete from staging area after successful import
        try:
            os.remove(filepath)
            current_app.logger.info(f"Removed staging file: {filepath}")
        except Exception as e:
            current_app.logger.warning(f"Failed to remove staging file {filepath}: {str(e)}")

        return jsonify({
            'success': True,
            'image_id': result['image_id'],
            'path': result['path'],
            'xxhash': result['xxhash'],
            'message': 'Image imported successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Error importing from staging: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Image Editor Interface ====================

@image_bp.route("/image-editor")
@login_required
def image_editor():
    """Image editor interface - renders the full web-based editor"""
    from flask import render_template
    return render_template('image_editor.html')

