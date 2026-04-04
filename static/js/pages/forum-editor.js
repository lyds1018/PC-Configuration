(function () {
    function insertAtCursor(input, text) {
        const start = input.selectionStart || 0;
        const end = input.selectionEnd || 0;
        const value = input.value || '';
        input.value = value.slice(0, start) + text + value.slice(end);
        const cursor = start + text.length;
        input.focus();
        input.setSelectionRange(cursor, cursor);
    }

    function notify(message, type) {
        if (window.PCConfig && typeof window.PCConfig.showNotification === 'function') {
            window.PCConfig.showNotification(message, type || 'info');
            return;
        }
        window.alert(message);
    }

    document.addEventListener('DOMContentLoaded', function () {
        const editor = document.querySelector('[data-forum-editor]');
        const textarea = document.getElementById('forum-post-content');
        if (!editor || !textarea) return;

        const emojiToggleBtn = editor.querySelector('[data-editor-action="emoji-toggle"]');
        const imageUploadBtn = editor.querySelector('[data-editor-action="image-upload"]');
        const emojiPanel = editor.querySelector('[data-editor-emoji-panel]');
        const fileInput = editor.querySelector('[data-editor-image-input]');
        const uploadUrl = editor.getAttribute('data-upload-url') || '';
        const form = textarea.closest('form');
        const csrfTokenEl = form ? form.querySelector('input[name="csrfmiddlewaretoken"]') : null;
        const csrfToken = csrfTokenEl ? csrfTokenEl.value : '';

        if (emojiToggleBtn && emojiPanel) {
            emojiToggleBtn.addEventListener('click', function () {
                emojiPanel.classList.toggle('hidden');
            });

            emojiPanel.addEventListener('click', function (event) {
                const btn = event.target.closest('[data-emoji]');
                if (!btn) return;
                const emoji = btn.getAttribute('data-emoji') || '';
                if (!emoji) return;
                insertAtCursor(textarea, emoji);
                emojiPanel.classList.add('hidden');
            });

            document.addEventListener('click', function (event) {
                if (!editor.contains(event.target)) {
                    emojiPanel.classList.add('hidden');
                }
            });
        }

        if (imageUploadBtn && fileInput) {
            imageUploadBtn.addEventListener('click', function () {
                fileInput.click();
            });

            fileInput.addEventListener('change', async function () {
                const file = fileInput.files && fileInput.files[0];
                if (!file) return;

                const formData = new FormData();
                formData.append('image', file);

                imageUploadBtn.disabled = true;
                imageUploadBtn.classList.add('is-loading');
                const label = imageUploadBtn.querySelector('.forum-tool-label');
                const originalLabel = label ? label.textContent : '';
                if (label) label.textContent = '上传中...';

                try {
                    const response = await fetch(uploadUrl, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken,
                        },
                        body: formData,
                    });
                    const data = await response.json();
                    if (!response.ok || !data.ok || !data.url) {
                        throw new Error(data.message || '上传失败');
                    }
                    insertAtCursor(textarea, `\n![图片](${data.url})\n`);
                    notify('图片已插入正文。', 'success');
                } catch (error) {
                    notify(error.message || '图片上传失败，请稍后重试。', 'error');
                } finally {
                    imageUploadBtn.disabled = false;
                    imageUploadBtn.classList.remove('is-loading');
                    if (label) label.textContent = originalLabel || '图片';
                    fileInput.value = '';
                }
            });
        }
    });
})();
