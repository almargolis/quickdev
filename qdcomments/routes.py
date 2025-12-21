"""
Routes for qdcomments.

Provides public comment submission/listing, moderation interface,
and admin configuration routes.
"""

from flask import current_app, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from qdcomments import comments_bp
from qdcomments.models import Comment, db
from qdcomments.filters import CommentContentProcessor
from datetime import datetime
import yaml


# Helper function to check user role
def require_role(*roles):
    """
    Decorator to require specific roles for a route.

    Args:
        *roles: One or more role names required to access the route
    """
    from functools import wraps

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            if current_user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# PUBLIC ROUTES
# ============================================================================

@comments_bp.route('/post', methods=['POST'])
@login_required
def post_comment():
    """
    Submit a new comment.

    POST JSON:
        content_type: Type of content ('article', 'product', etc.)
        content_id: Content identifier (slug, ID, etc.)
        content: Comment text
        parent_id: Optional parent comment ID for threading

    Returns:
        JSON: {'success': true, 'comment_id': 123, 'status': 'p'}
    """
    if not current_app.config.get('COMMENTS_ENABLED', True):
        return jsonify({'error': 'Comments are disabled'}), 403

    data = request.get_json()

    # Validate required fields
    if not data or not data.get('content_type') or not data.get('content_id') or not data.get('content'):
        return jsonify({'error': 'Missing required fields'}), 400

    content = data['content'].strip()
    content_type = data['content_type']
    content_id = data['content_id']
    parent_id = data.get('parent_id')

    # Validate content length
    max_length = current_app.config.get('COMMENT_MAX_LENGTH', 5000)
    if len(content) > max_length:
        return jsonify({'error': f'Comment exceeds maximum length of {max_length} characters'}), 400

    if len(content) == 0:
        return jsonify({'error': 'Comment cannot be empty'}), 400

    # Validate parent_id if threading
    if parent_id:
        if not current_app.config.get('ALLOW_THREADING', True):
            return jsonify({'error': 'Comment threading is disabled'}), 400

        parent = Comment.query.get(parent_id)
        if not parent:
            return jsonify({'error': 'Parent comment not found'}), 404

        # Check thread depth
        depth = 1
        check_parent = parent
        max_depth = current_app.config.get('MAX_THREAD_DEPTH', 3)
        while check_parent.parent_id:
            depth += 1
            if depth >= max_depth:
                return jsonify({'error': f'Maximum thread depth ({max_depth}) exceeded'}), 400
            check_parent = Comment.query.get(check_parent.parent_id)

    # Get user's comment settings (snapshot at comment time)
    user_comment_style = getattr(current_user, 'comment_style', 't')
    user_moderation_level = getattr(current_user, 'moderation_level', '1')

    # Process content through filter
    blocked_words_path = current_app.config.get('BLOCKED_WORDS_PATH')
    processor = CommentContentProcessor(blocked_words_path)
    processed_html, is_clean, blocked_words_found = processor.process_comment(content, user_comment_style)

    # Determine status based on moderation level and blocked words
    if user_moderation_level == '0':
        # Blocked users
        status = 'b'
        status_reason = 'a'
    elif not is_clean:
        # Blocked words detected
        status = 'm'
        status_reason = 'd'
    elif user_moderation_level == '1':
        # Requires moderation
        status = 'm'
        status_reason = 'a'
    else:  # user_moderation_level == '9'
        # Auto-approved
        status = 'p'
        status_reason = 'a'

    # Create comment
    comment = Comment(
        user_id=current_user.id,
        content_type=content_type,
        content_id=content_id,
        content=content,  # Store raw content
        user_comment_style=user_comment_style,
        user_moderation_level=user_moderation_level,
        status=status,
        status_reason=status_reason,
        parent_id=parent_id
    )

    db.session.add(comment)
    db.session.commit()

    return jsonify({
        'success': True,
        'comment_id': comment.id,
        'status': status,
        'message': 'Comment posted' if status == 'p' else 'Comment submitted for moderation'
    }), 201


@comments_bp.route('/list/<content_type>/<path:content_id>')
def list_comments(content_type, content_id):
    """
    Get comments for specific content.

    Query params:
        page: Pagination (default: 1)
        sort: 'newest', 'oldest' (default: 'newest')

    Returns:
        JSON list of comments with status='p' only
    """
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'newest')

    per_page = current_app.config.get('COMMENTS_PER_PAGE', 50)

    # Build query
    query = Comment.get_for_content(content_type, content_id, status='p', include_replies=True)

    # Apply sorting
    if sort == 'oldest':
        query = query.order_by(Comment.created_at.asc())
    else:  # newest
        query = query.order_by(Comment.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    comments = pagination.items

    # Process comments for display
    blocked_words_path = current_app.config.get('BLOCKED_WORDS_PATH')
    processor = CommentContentProcessor(blocked_words_path)

    comment_list = []
    for comment in comments:
        processed_html, _, _ = processor.process_comment(comment.content, comment.user_comment_style)

        comment_list.append({
            'id': comment.id,
            'user': {
                'id': comment.user_id,
                'username': comment.user.username if comment.user else 'Unknown'
            },
            'content_html': processed_html,
            'parent_id': comment.parent_id,
            'created_at': comment.created_at.isoformat(),
            'updated_at': comment.updated_at.isoformat() if comment.updated_at else None
        })

    return jsonify({
        'comments': comment_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@comments_bp.route('/count/<content_type>/<path:content_id>')
def count_comments(content_type, content_id):
    """
    Quick count of approved comments.

    Returns:
        JSON: {'count': 42}
    """
    count = Comment.count_for_content(content_type, content_id, status='p')
    return jsonify({'count': count})


# ============================================================================
# MODERATION ROUTES (admin/editor only)
# ============================================================================

@comments_bp.route('/moderation/queue')
@login_required
@require_role('admin', 'editor')
def moderation_queue():
    """
    View all comments pending moderation.

    Shows comments with status='m' for approval/rejection.
    """
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('COMMENTS_PER_PAGE', 50)

    pagination = Comment.get_pending_moderation().paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Process comments for display
    blocked_words_path = current_app.config.get('BLOCKED_WORDS_PATH')
    processor = CommentContentProcessor(blocked_words_path)

    comments_data = []
    for comment in pagination.items:
        processed_html, _, blocked_words = processor.process_comment(
            comment.content, comment.user_comment_style
        )

        comments_data.append({
            'comment': comment,
            'content_html': processed_html,
            'blocked_words': blocked_words if comment.status_reason == 'd' else []
        })

    return render_template(
        'qdcomments/moderation_queue.html',
        comments=comments_data,
        pagination=pagination
    )


@comments_bp.route('/moderation/approve/<int:comment_id>', methods=['POST'])
@login_required
@require_role('admin', 'editor')
def approve_comment(comment_id):
    """
    Approve a comment (change status from 'm' to 'p').

    Returns:
        Redirect to moderation queue or JSON response
    """
    comment = Comment.query.get_or_404(comment_id)

    if comment.status != 'm':
        if request.is_json:
            return jsonify({'error': 'Comment is not pending moderation'}), 400
        flash('Comment is not pending moderation', 'error')
        return redirect(url_for('comments.moderation_queue'))

    comment.approve(current_user.id)

    if request.is_json:
        return jsonify({'success': True, 'message': 'Comment approved'})

    flash('Comment approved', 'success')
    return redirect(url_for('comments.moderation_queue'))


@comments_bp.route('/moderation/reject/<int:comment_id>', methods=['POST'])
@login_required
@require_role('admin', 'editor')
def reject_comment(comment_id):
    """
    Reject a comment (change status from 'm' to 'b').

    Returns:
        Redirect to moderation queue or JSON response
    """
    comment = Comment.query.get_or_404(comment_id)

    if comment.status != 'm':
        if request.is_json:
            return jsonify({'error': 'Comment is not pending moderation'}), 400
        flash('Comment is not pending moderation', 'error')
        return redirect(url_for('comments.moderation_queue'))

    comment.reject(current_user.id)

    if request.is_json:
        return jsonify({'success': True, 'message': 'Comment rejected'})

    flash('Comment rejected', 'success')
    return redirect(url_for('comments.moderation_queue'))


@comments_bp.route('/moderation/activity')
@login_required
@require_role('admin', 'editor')
def global_activity():
    """
    View all comments with filtering options.

    Query params:
        status: Filter by status (p/m/b/all)
        content_type: Filter by content type
        user_id: Filter by user
        page: Pagination
    """
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    content_type_filter = request.args.get('content_type')
    user_id_filter = request.args.get('user_id', type=int)

    per_page = current_app.config.get('COMMENTS_PER_PAGE', 50)

    # Build query
    query = Comment.query

    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    if content_type_filter:
        query = query.filter_by(content_type=content_type_filter)

    if user_id_filter:
        query = query.filter_by(user_id=user_id_filter)

    # Sort by newest first
    query = query.order_by(Comment.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Process comments for display
    blocked_words_path = current_app.config.get('BLOCKED_WORDS_PATH')
    processor = CommentContentProcessor(blocked_words_path)

    comments_data = []
    for comment in pagination.items:
        processed_html, _, _ = processor.process_comment(
            comment.content, comment.user_comment_style
        )

        comments_data.append({
            'comment': comment,
            'content_html': processed_html
        })

    return render_template(
        'qdcomments/moderation_activity.html',
        comments=comments_data,
        pagination=pagination,
        status_filter=status_filter,
        content_type_filter=content_type_filter,
        user_id_filter=user_id_filter
    )


# ============================================================================
# ADMIN ROUTES (admin only)
# ============================================================================

@comments_bp.route('/admin/blocked-words', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def edit_blocked_words():
    """
    Edit blocked_words.yaml file.

    GET: Display current content in textarea
    POST: Save updated content with validation
    """
    blocked_words_path = current_app.config.get('BLOCKED_WORDS_PATH')

    if request.method == 'POST':
        new_content = request.form.get('content', '')

        # Validate YAML syntax
        try:
            yaml.safe_load(new_content)
        except yaml.YAMLError as e:
            flash(f'Invalid YAML syntax: {e}', 'error')
            return render_template(
                'qdcomments/blocked_words_edit.html',
                content=new_content,
                path=blocked_words_path
            )

        # Save to file
        try:
            with open(blocked_words_path, 'w') as f:
                f.write(new_content)
            flash('blocked_words.yaml updated successfully', 'success')

            # Reload the filter
            processor = CommentContentProcessor(blocked_words_path)
            processor.reload_blocked_words()

        except Exception as e:
            flash(f'Error saving file: {e}', 'error')
            return render_template(
                'qdcomments/blocked_words_edit.html',
                content=new_content,
                path=blocked_words_path
            )

    # Load current content
    try:
        with open(blocked_words_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        content = "# blocked_words.yaml not found\n# Creating new file\nwords: []\ncase_sensitive: false\nwhole_word_only: true"

    return render_template(
        'qdcomments/blocked_words_edit.html',
        content=content,
        path=blocked_words_path
    )


@comments_bp.route('/admin/config', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def edit_config():
    """
    Toggle global comment settings.

    Note: This provides a UI but settings are stored in app.config
    which is loaded from environment variables. Changes here are runtime-only.
    For persistent changes, update .env file.
    """
    if request.method == 'POST':
        # Update runtime config (not persistent)
        current_app.config['COMMENTS_ENABLED'] = request.form.get('comments_enabled') == 'on'
        current_app.config['COMMENTS_REQUIRE_LOGIN'] = request.form.get('require_login') == 'on'
        current_app.config['ALLOW_THREADING'] = request.form.get('allow_threading') == 'on'

        flash('Configuration updated (runtime only - update .env for persistence)', 'success')

    config_data = {
        'comments_enabled': current_app.config.get('COMMENTS_ENABLED', True),
        'require_login': current_app.config.get('COMMENTS_REQUIRE_LOGIN', True),
        'allow_threading': current_app.config.get('ALLOW_THREADING', True),
        'comments_per_page': current_app.config.get('COMMENTS_PER_PAGE', 50),
        'comment_max_length': current_app.config.get('COMMENT_MAX_LENGTH', 5000),
        'max_thread_depth': current_app.config.get('MAX_THREAD_DEPTH', 3)
    }

    return render_template(
        'qdcomments/config_edit.html',
        config=config_data
    )
