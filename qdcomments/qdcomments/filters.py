"""
Content filtering and processing for qdcomments.

Provides blocked words filtering, HTML sanitization, and content processing
based on user comment style permissions.
"""

import yaml
import re
import html as html_module
import markdown
import os
from pathlib import Path


class BlockedWordsFilter:
    """Checks content against blocked words list."""

    def __init__(self, blocked_words_path):
        """
        Initialize blocked words filter.

        Args:
            blocked_words_path: Path to blocked_words.yaml file
        """
        self.blocked_words_path = blocked_words_path
        self.blocked_words = self._load_blocked_words()
        self.case_sensitive = False
        self.whole_word_only = True

    def _load_blocked_words(self):
        """Load blocked words from YAML file."""
        try:
            with open(self.blocked_words_path, 'r') as f:
                data = yaml.safe_load(f) or {}

                # Update settings from file
                self.case_sensitive = data.get('case_sensitive', False)
                self.whole_word_only = data.get('whole_word_only', True)

                # Get word list
                words = data.get('words', [])
                if not self.case_sensitive:
                    words = [w.lower() for w in words]

                return words
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error loading blocked words: {e}")
            return []

    def reload(self):
        """Reload blocked words from file."""
        self.blocked_words = self._load_blocked_words()

    def check_content(self, content):
        """
        Check if content contains blocked words.

        Args:
            content: Text content to check

        Returns:
            (is_clean, matched_words) tuple
            - is_clean: True if no blocked words found
            - matched_words: List of matched blocked words
        """
        if not self.blocked_words:
            return (True, [])

        content_to_check = content if self.case_sensitive else content.lower()
        matched = []

        for word in self.blocked_words:
            if self.whole_word_only:
                # Whole-word matching using word boundaries
                pattern = r'\b' + re.escape(word) + r'\b'
                if re.search(pattern, content_to_check):
                    matched.append(word)
            else:
                # Substring matching
                if word in content_to_check:
                    matched.append(word)

        return (len(matched) == 0, matched)


class HTMLSanitizer:
    """Sanitize HTML to only allow safe tags (for comment_style='h')."""

    ALLOWED_TAGS = {'b', 'i', 'strong', 'em', 'a', 'br'}
    ALLOWED_ATTRS = {'a': ['href', 'title']}

    def sanitize(self, html_content):
        """
        Strip all HTML except allowed tags.

        Args:
            html_content: HTML string to sanitize

        Returns:
            Sanitized HTML string
        """
        # Strip all tags except allowed
        allowed_pattern = '|'.join(self.ALLOWED_TAGS)

        # Remove all tags NOT in allowed list
        # Keep <b>, <i>, <strong>, <em>, <a>, <br>
        cleaned = re.sub(
            r'<(?!/?(?:' + allowed_pattern + r')\b)[^>]+>',
            '',
            html_content
        )

        # Sanitize <a> tags to only have href/title
        def clean_link(match):
            full_tag = match.group(0)

            # Extract href if present
            href_match = re.search(r'href=["\']([^"\']+)["\']', full_tag)
            title_match = re.search(r'title=["\']([^"\']+)["\']', full_tag)

            href = href_match.group(1) if href_match else ''
            title = title_match.group(1) if title_match else ''

            # Only allow http/https links
            if not href.startswith(('http://', 'https://')):
                return ''  # Strip invalid links

            result = f'<a href="{html_module.escape(href)}"'
            if title:
                result += f' title="{html_module.escape(title)}"'
            result += '>'
            return result

        cleaned = re.sub(r'<a[^>]*>', clean_link, cleaned)

        return cleaned


class CommentContentProcessor:
    """Process comment content based on comment_style."""

    def __init__(self, blocked_words_path):
        """
        Initialize content processor.

        Args:
            blocked_words_path: Path to blocked_words.yaml file
        """
        self.blocked_words_filter = BlockedWordsFilter(blocked_words_path)
        self.html_sanitizer = HTMLSanitizer()

    def reload_blocked_words(self):
        """Reload blocked words from file."""
        self.blocked_words_filter.reload()

    def process_comment(self, content, comment_style):
        """
        Process comment content based on style.

        Args:
            content: Raw comment content
            comment_style: 't' (text), 'h' (HTML), or 'm' (markdown)

        Returns:
            (processed_html, is_clean, blocked_words_found) tuple
            - processed_html: Rendered HTML for display
            - is_clean: True if no blocked words found
            - blocked_words_found: List of blocked words that matched
        """
        # Check blocked words first (on raw content)
        is_clean, blocked_words = self.blocked_words_filter.check_content(content)

        # Process based on style
        if comment_style == 't':
            # Plain text - escape HTML entities, preserve line breaks
            processed = html_module.escape(content)
            processed = processed.replace('\n', '<br>')

        elif comment_style == 'h':
            # Limited HTML - sanitize to allowed tags only
            processed = self.html_sanitizer.sanitize(content)

        elif comment_style == 'm':
            # Markdown - convert to HTML (safe, no raw HTML allowed)
            md = markdown.Markdown(
                extensions=['fenced_code', 'nl2br', 'tables'],
                output_format='html5'
            )
            # Escape any raw HTML first
            safe_content = content.replace('<', '&lt;').replace('>', '&gt;')
            processed = md.convert(safe_content)

        else:
            # Fallback to text
            processed = html_module.escape(content)
            processed = processed.replace('\n', '<br>')

        return processed, is_clean, blocked_words


def initialize_blocked_words(path):
    """
    Create default blocked_words.yaml from built-in list.

    Args:
        path: Destination path for blocked_words.yaml
    """
    import shutil
    from pathlib import Path as PathLib

    # Copy from package data
    default_path = PathLib(__file__).parent / 'data' / 'default_blocked_words.yaml'

    if default_path.exists():
        shutil.copy(default_path, path)
    else:
        # If default doesn't exist, create a minimal one
        minimal_config = {
            'words': [
                'spam',
                'viagra',
                'casino',
            ],
            'case_sensitive': False,
            'whole_word_only': True
        }

        with open(path, 'w') as f:
            yaml.dump(minimal_config, f, default_flow_style=False, sort_keys=False)
